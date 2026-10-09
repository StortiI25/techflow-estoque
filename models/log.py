from database.database import execute, like, paginar, query


def inserir(usuario_id, acao, entidade, entidade_id, descricao, ip):
    execute("INSERT INTO logs(usuario_id,acao,entidade,entidade_id,descricao,ip) VALUES(?,?,?,?,?,?)",
            (usuario_id, acao, entidade, entidade_id, descricao, ip))


def listar(filtros, pagina, por_pagina):
    sql = """SELECT l.*, u.nome AS usuario FROM logs l LEFT JOIN usuarios u ON u.id=l.usuario_id WHERE 1=1"""
    params = []
    if filtros.get("acao"):
        sql += " AND l.acao=?"; params.append(filtros["acao"])
    if filtros.get("usuario_id"):
        sql += " AND l.usuario_id=?"; params.append(int(filtros["usuario_id"]))
    if filtros.get("q"):
        sql += " AND (l.descricao LIKE ? ESCAPE '\\' OR l.entidade LIKE ? ESCAPE '\\')"; params += [like(filtros["q"])] * 2
    if filtros.get("data_inicio"):
        sql += " AND date(l.data_hora)>=date(?)"; params.append(filtros["data_inicio"])
    if filtros.get("data_fim"):
        sql += " AND date(l.data_hora)<=date(?)"; params.append(filtros["data_fim"])
    return paginar(sql + " ORDER BY l.id DESC", tuple(params), pagina, por_pagina)


def acoes():
    return [r["acao"] for r in query("SELECT DISTINCT acao FROM logs ORDER BY acao")]
