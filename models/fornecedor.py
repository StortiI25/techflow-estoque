from database.database import execute, like, paginar, query, scalar
from utils.validators import ESTADOS, cnpj_valido, email_valido, so_digitos


def obter(id):
    return query("SELECT * FROM fornecedores WHERE id=?", (id,), one=True)


def listar_ativos():
    return query("SELECT id, COALESCE(nome_fantasia, razao_social) AS nome FROM fornecedores WHERE ativo=1 ORDER BY nome")


def listar(busca, pagina, por_pagina):
    sql, params = "SELECT * FROM fornecedores WHERE 1=1", []
    if busca:
        sql += " AND (razao_social LIKE ? ESCAPE '\\' OR nome_fantasia LIKE ? ESCAPE '\\' OR cnpj LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\')"
        params += [like(busca), like(busca), like(so_digitos(busca) or busca), like(busca)]
    return paginar(sql + " ORDER BY ativo DESC, razao_social", tuple(params), pagina, por_pagina)


def validar(form, ignorar_id=None):
    campos = ("razao_social", "nome_fantasia", "cnpj", "email", "telefone", "endereco", "cidade", "estado", "observacoes")
    d = {k: (form.get(k) or "").strip() for k in campos}
    d["cnpj"] = so_digitos(d["cnpj"])
    e = {}
    if not d["razao_social"]:
        e["razao_social"] = "A razão social é obrigatória."
    if d["cnpj"]:
        if not cnpj_valido(d["cnpj"]):
            e["cnpj"] = "CNPJ inválido."
        elif scalar("SELECT COUNT(*) FROM fornecedores WHERE cnpj=? AND id<>?", (d["cnpj"], ignorar_id or 0)):
            e["cnpj"] = "Já existe um fornecedor com este CNPJ."
    if d["email"] and not email_valido(d["email"]):
        e["email"] = "Informe um e-mail válido."
    if d["estado"] and d["estado"].upper() not in ESTADOS:
        e["estado"] = "UF inválida."
    d["estado"] = d["estado"].upper()
    return d, e


def criar(d):
    cur = execute("""INSERT INTO fornecedores(razao_social,nome_fantasia,cnpj,email,telefone,endereco,cidade,estado,observacoes)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (d["razao_social"], d["nome_fantasia"] or None, d["cnpj"] or None, d["email"] or None, d["telefone"] or None,
                   d["endereco"] or None, d["cidade"] or None, d["estado"] or None, d["observacoes"] or None))
    return cur.lastrowid


def atualizar(id, d):
    execute("""UPDATE fornecedores SET razao_social=?,nome_fantasia=?,cnpj=?,email=?,telefone=?,endereco=?,cidade=?,estado=?,observacoes=? WHERE id=?""",
            (d["razao_social"], d["nome_fantasia"] or None, d["cnpj"] or None, d["email"] or None, d["telefone"] or None,
             d["endereco"] or None, d["cidade"] or None, d["estado"] or None, d["observacoes"] or None, id))


def definir_ativo(id, ativo):
    execute("UPDATE fornecedores SET ativo=? WHERE id=?", (1 if ativo else 0, id))


def detalhes(id):
    produtos = query("""SELECT id, sku, nome, estoque_atual, preco_custo FROM produtos
                        WHERE fornecedor_id=? AND ativo=1 ORDER BY nome""", (id,))
    entradas = query("""SELECT m.*, p.nome AS produto FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
                        WHERE m.fornecedor_id=? AND m.tipo='entrada' ORDER BY m.data_hora DESC, m.id DESC LIMIT 15""", (id,))
    total = scalar("SELECT COALESCE(SUM(valor_total),0) FROM movimentacoes WHERE fornecedor_id=? AND tipo='entrada'", (id,))
    ultima = scalar("SELECT MAX(data_hora) FROM movimentacoes WHERE fornecedor_id=?", (id,), padrao=None)
    return {"produtos": produtos, "entradas": entradas, "total_comprado": total, "ultima_movimentacao": ultima}
