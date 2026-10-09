from database.database import execute, like, paginar, query, scalar
from utils.validators import ESTADOS, cnpj_valido, cpf_valido, email_valido, so_digitos


def obter(id):
    return query("SELECT * FROM clientes WHERE id=?", (id,), one=True)


def listar_ativos():
    return query("SELECT id, nome FROM clientes WHERE ativo=1 ORDER BY nome")


def listar(busca, pagina, por_pagina):
    sql, params = "SELECT * FROM clientes WHERE 1=1", []
    if busca:
        sql += " AND (nome LIKE ? ESCAPE '\\' OR documento LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\')"
        params += [like(busca), like(so_digitos(busca) or busca), like(busca)]
    return paginar(sql + " ORDER BY ativo DESC, nome", tuple(params), pagina, por_pagina)


def validar(form, ignorar_id=None):
    d = {k: (form.get(k) or "").strip() for k in ("nome", "documento", "email", "telefone", "endereco", "cidade", "estado")}
    d["documento"] = so_digitos(d["documento"])
    e = {}
    if not d["nome"]:
        e["nome"] = "O nome é obrigatório."
    if d["documento"]:
        if not (cpf_valido(d["documento"]) or cnpj_valido(d["documento"])):
            e["documento"] = "CPF ou CNPJ inválido."
        elif scalar("SELECT COUNT(*) FROM clientes WHERE documento=? AND id<>?", (d["documento"], ignorar_id or 0)):
            e["documento"] = "Já existe um cliente com este documento."
    if d["email"] and not email_valido(d["email"]):
        e["email"] = "Informe um e-mail válido."
    if d["estado"] and d["estado"].upper() not in ESTADOS:
        e["estado"] = "UF inválida."
    d["estado"] = d["estado"].upper()
    return d, e


def criar(d):
    return execute("INSERT INTO clientes(nome,documento,email,telefone,endereco,cidade,estado) VALUES(?,?,?,?,?,?,?)",
                   (d["nome"], d["documento"] or None, d["email"] or None, d["telefone"] or None,
                    d["endereco"] or None, d["cidade"] or None, d["estado"] or None)).lastrowid


def atualizar(id, d):
    execute("UPDATE clientes SET nome=?,documento=?,email=?,telefone=?,endereco=?,cidade=?,estado=? WHERE id=?",
            (d["nome"], d["documento"] or None, d["email"] or None, d["telefone"] or None,
             d["endereco"] or None, d["cidade"] or None, d["estado"] or None, id))


def definir_ativo(id, ativo):
    execute("UPDATE clientes SET ativo=? WHERE id=?", (1 if ativo else 0, id))


def detalhes(id):
    saidas = query("""SELECT m.*, p.nome AS produto FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
                      WHERE m.cliente_id=? AND m.tipo='saida' ORDER BY m.data_hora DESC, m.id DESC LIMIT 20""", (id,))
    resumo = query("""SELECT COUNT(DISTINCT produto_id) AS produtos, COALESCE(SUM(quantidade),0) AS quantidade,
                             COALESCE(SUM(valor_total),0) AS valor_total, MAX(data_hora) AS ultima
                      FROM movimentacoes WHERE cliente_id=? AND tipo='saida'""", (id,), one=True)
    return {"saidas": saidas, "resumo": resumo}
