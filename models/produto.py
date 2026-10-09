import os
import uuid

from werkzeug.utils import secure_filename

from database.database import execute, like, paginar, query, scalar
from utils.validators import parse_decimal, parse_int

UNIDADES = ["unidade", "caixa", "pacote", "kg", "litro", "metro"]
STATUS_SQL = "CASE WHEN p.estoque_atual<=0 THEN 'esgotado' WHEN p.estoque_atual<=p.estoque_minimo THEN 'baixo' ELSE 'normal' END"
BASE_SQL = f"""SELECT p.*, c.nome AS categoria, COALESCE(f.nome_fantasia, f.razao_social) AS fornecedor,
               {STATUS_SQL} AS status
               FROM produtos p JOIN categorias c ON c.id=p.categoria_id
               LEFT JOIN fornecedores f ON f.id=p.fornecedor_id"""


def obter(id):
    return query(BASE_SQL + " WHERE p.id=?", (id,), one=True)


def filtrar(f):
    """Monta (WHERE, params) a partir dos filtros; usado também nos relatórios."""
    sql, params = " WHERE 1=1", []
    ativo = f.get("ativo", "1")
    if ativo in ("0", "1"):
        sql += " AND p.ativo=?"
        params.append(int(ativo))
    if f.get("q"):
        sql += " AND (p.nome LIKE ? ESCAPE '\\' OR p.sku LIKE ? ESCAPE '\\' OR p.codigo_barras LIKE ? ESCAPE '\\')"
        params += [like(f["q"])] * 3
    if f.get("categoria_id"):
        sql += " AND p.categoria_id=?"
        params.append(int(f["categoria_id"]))
    if f.get("fornecedor_id"):
        sql += " AND p.fornecedor_id=?"
        params.append(int(f["fornecedor_id"]))
    status = f.get("status")
    if status == "esgotado":
        sql += " AND p.estoque_atual<=0"
    elif status == "baixo":
        sql += " AND p.estoque_atual>0 AND p.estoque_atual<=p.estoque_minimo"
    elif status == "normal":
        sql += " AND p.estoque_atual>p.estoque_minimo"
    nivel = f.get("estoque")
    if nivel == "com":
        sql += " AND p.estoque_atual>0"
    elif nivel == "sem":
        sql += " AND p.estoque_atual=0"
    elif nivel == "acima_maximo":
        sql += " AND p.estoque_maximo IS NOT NULL AND p.estoque_maximo>0 AND p.estoque_atual>p.estoque_maximo"
    return sql, params


def listar(filtros, pagina, por_pagina):
    where, params = filtrar(filtros)
    return paginar(BASE_SQL + where + " ORDER BY p.nome", tuple(params), pagina, por_pagina)


def opcoes_movimentacao():
    return query("SELECT id, sku, nome, estoque_atual, unidade FROM produtos WHERE ativo=1 ORDER BY nome")


def validar(form, ignorar_id=None, inclui_estoque_inicial=False):
    d = {k: (form.get(k) or "").strip() for k in ("nome", "sku", "codigo_barras", "descricao", "unidade")}
    e = {}
    d["sku"] = d["sku"].upper()
    if not d["nome"]:
        e["nome"] = "O nome do produto é obrigatório."
    if not d["sku"]:
        e["sku"] = "O SKU é obrigatório."
    elif scalar("SELECT COUNT(*) FROM produtos WHERE sku=? AND id<>?", (d["sku"], ignorar_id or 0)):
        e["sku"] = "Já existe um produto com este SKU."
    if d["codigo_barras"] and scalar("SELECT COUNT(*) FROM produtos WHERE codigo_barras=? AND id<>?", (d["codigo_barras"], ignorar_id or 0)):
        e["codigo_barras"] = "Já existe um produto com este código de barras."
    if d["unidade"] not in UNIDADES:
        e["unidade"] = "Unidade de medida inválida."
    try:
        d["categoria_id"] = int(form.get("categoria_id") or 0)
        if not scalar("SELECT COUNT(*) FROM categorias WHERE id=? AND ativo=1", (d["categoria_id"],)):
            raise ValueError
    except ValueError:
        e["categoria_id"] = "Selecione uma categoria válida."
    try:
        d["fornecedor_id"] = int(form["fornecedor_id"]) if form.get("fornecedor_id") else None
        if d["fornecedor_id"] and not scalar("SELECT COUNT(*) FROM fornecedores WHERE id=?", (d["fornecedor_id"],)):
            raise ValueError
    except ValueError:
        e["fornecedor_id"] = "Fornecedor inválido."

    def decimal(campo, rotulo, obrigatorio=False):
        try:
            v = parse_decimal(form.get(campo))
        except ValueError:
            e[campo] = f"{rotulo}: informe um valor numérico."
            return 0
        if v is None:
            if obrigatorio:
                e[campo] = f"{rotulo} é obrigatório."
            return 0
        if v < 0:
            e[campo] = f"{rotulo} não pode ser negativo."
        return v

    def inteiro(campo, rotulo, obrigatorio=False):
        try:
            v = parse_int(form.get(campo))
        except ValueError:
            e[campo] = f"{rotulo}: informe um número inteiro."
            return None
        if v is None:
            if obrigatorio:
                e[campo] = f"{rotulo} é obrigatório."
            return None
        if v < 0:
            e[campo] = f"{rotulo} não pode ser negativo."
        return v

    d["preco_custo"] = decimal("preco_custo", "Preço de custo", True)
    d["preco_venda"] = decimal("preco_venda", "Preço de venda")
    d["estoque_minimo"] = inteiro("estoque_minimo", "Estoque mínimo", True) or 0
    d["estoque_maximo"] = inteiro("estoque_maximo", "Estoque máximo")
    if d["estoque_maximo"] is not None and "estoque_maximo" not in e and d["estoque_maximo"] < d["estoque_minimo"]:
        e["estoque_maximo"] = "O estoque máximo não pode ser menor que o mínimo."
    if inclui_estoque_inicial:
        d["quantidade_inicial"] = inteiro("quantidade_inicial", "Quantidade inicial") or 0
    return d, e


def salvar_imagem(arquivo, extensoes, pasta):
    """Valida extensão e salva com nome aleatório. Retorna o nome do arquivo ou None."""
    if not arquivo or not arquivo.filename:
        return None, None
    ext = secure_filename(arquivo.filename).rsplit(".", 1)[-1].lower() if "." in arquivo.filename else ""
    if ext not in extensoes:
        return None, "Imagem inválida. Use PNG, JPG ou WEBP."
    cabecalho = arquivo.stream.read(12)
    arquivo.stream.seek(0)
    ok = cabecalho.startswith(b"\x89PNG") or cabecalho.startswith(b"\xff\xd8\xff") or (cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP")
    if not ok:
        return None, "O arquivo enviado não é uma imagem válida."
    os.makedirs(pasta, exist_ok=True)
    nome = f"{uuid.uuid4().hex}.{ext}"
    arquivo.save(os.path.join(pasta, nome))
    return nome, None


def inserir(d, imagem=None):
    """Insere o produto com estoque 0; o estoque inicial entra como movimentação."""
    return execute("""INSERT INTO produtos(sku,codigo_barras,nome,descricao,categoria_id,fornecedor_id,preco_custo,preco_venda,
                      estoque_atual,estoque_minimo,estoque_maximo,unidade,imagem) VALUES(?,?,?,?,?,?,?,?,0,?,?,?,?)""",
                   (d["sku"], d["codigo_barras"] or None, d["nome"], d["descricao"] or None, d["categoria_id"], d["fornecedor_id"],
                    d["preco_custo"], d["preco_venda"], d["estoque_minimo"], d["estoque_maximo"], d["unidade"], imagem)).lastrowid


def atualizar(id, d, imagem=None):
    """Nunca altera estoque_atual: o saldo só muda por movimentações."""
    execute("""UPDATE produtos SET sku=?,codigo_barras=?,nome=?,descricao=?,categoria_id=?,fornecedor_id=?,preco_custo=?,preco_venda=?,
               estoque_minimo=?,estoque_maximo=?,unidade=?,imagem=COALESCE(?,imagem),atualizado_em=datetime('now','localtime') WHERE id=?""",
            (d["sku"], d["codigo_barras"] or None, d["nome"], d["descricao"] or None, d["categoria_id"], d["fornecedor_id"],
             d["preco_custo"], d["preco_venda"], d["estoque_minimo"], d["estoque_maximo"], d["unidade"], imagem, id))


def definir_ativo(id, ativo):
    execute("UPDATE produtos SET ativo=?, atualizado_em=datetime('now','localtime') WHERE id=?", (1 if ativo else 0, id))


def evolucao_estoque(id, limite=60):
    """Série de pontos (data, estoque_posterior) reconstruída das movimentações."""
    linhas = query("""SELECT data_hora, estoque_posterior FROM (
                        SELECT data_hora, estoque_posterior, id FROM movimentacoes WHERE produto_id=? ORDER BY data_hora DESC, id DESC LIMIT ?
                      ) ORDER BY data_hora, id""", (id, limite))
    return [{"data": r["data_hora"], "estoque": r["estoque_posterior"]} for r in linhas]
