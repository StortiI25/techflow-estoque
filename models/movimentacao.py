from database.database import execute, like, paginar, query

BASE_SQL = """SELECT m.*, p.nome AS produto, p.sku, p.unidade, u.nome AS usuario,
                     cl.nome AS cliente, COALESCE(f.nome_fantasia, f.razao_social) AS fornecedor,
                     (m.estoque_posterior - m.estoque_anterior) AS delta
              FROM movimentacoes m
              JOIN produtos p ON p.id=m.produto_id
              JOIN usuarios u ON u.id=m.usuario_id
              LEFT JOIN clientes cl ON cl.id=m.cliente_id
              LEFT JOIN fornecedores f ON f.id=m.fornecedor_id"""


def filtrar(f):
    sql, params = " WHERE 1=1", []
    if f.get("produto_id"):
        sql += " AND m.produto_id=?"; params.append(int(f["produto_id"]))
    if f.get("tipo") in ("entrada", "saida", "ajuste"):
        sql += " AND m.tipo=?"; params.append(f["tipo"])
    if f.get("usuario_id"):
        sql += " AND m.usuario_id=?"; params.append(int(f["usuario_id"]))
    if f.get("motivo"):
        sql += " AND m.motivo=?"; params.append(f["motivo"])
    if f.get("data_inicio"):
        sql += " AND date(m.data_hora)>=date(?)"; params.append(f["data_inicio"])
    if f.get("data_fim"):
        sql += " AND date(m.data_hora)<=date(?)"; params.append(f["data_fim"])
    if f.get("q"):
        sql += " AND (p.nome LIKE ? ESCAPE '\\' OR p.sku LIKE ? ESCAPE '\\')"; params += [like(f["q"])] * 2
    return sql, params


def listar(filtros, pagina, por_pagina):
    where, params = filtrar(filtros)
    return paginar(BASE_SQL + where + " ORDER BY m.data_hora DESC, m.id DESC", tuple(params), pagina, por_pagina)


def obter(id):
    return query(BASE_SQL + " WHERE m.id=?", (id,), one=True)


def recentes(limite=5):
    return query(BASE_SQL + " ORDER BY m.data_hora DESC, m.id DESC LIMIT ?", (limite,))


def do_produto(produto_id, limite=50):
    return query(BASE_SQL + " WHERE m.produto_id=? ORDER BY m.data_hora DESC, m.id DESC LIMIT ?", (produto_id, limite))


def motivos_usados():
    return [r["motivo"] for r in query("SELECT DISTINCT motivo FROM movimentacoes ORDER BY motivo")]


def inserir(dados):
    return execute("""INSERT INTO movimentacoes(produto_id,usuario_id,cliente_id,fornecedor_id,tipo,motivo,quantidade,
                      estoque_anterior,estoque_posterior,valor_unitario,valor_total,observacao,data_hora)
                      VALUES(:produto_id,:usuario_id,:cliente_id,:fornecedor_id,:tipo,:motivo,:quantidade,
                      :estoque_anterior,:estoque_posterior,:valor_unitario,:valor_total,:observacao,
                      COALESCE(:data_hora, datetime('now','localtime')))""", dados).lastrowid
