from database.database import execute, paginar, query, scalar


def criar(tipo, titulo, mensagem="", produto_id=None, usuario_id=None):
    return execute("INSERT INTO notificacoes(usuario_id,produto_id,tipo,titulo,mensagem) VALUES(?,?,?,?,?)",
                   (usuario_id, produto_id, tipo, titulo, mensagem)).lastrowid


def nao_lidas():
    return scalar("SELECT COUNT(*) FROM notificacoes WHERE lida=0")


def recentes(limite=6):
    return query("SELECT * FROM notificacoes ORDER BY criada_em DESC, id DESC LIMIT ?", (limite,))


def listar(somente_nao_lidas, tipo, pagina, por_pagina):
    sql, params = "SELECT * FROM notificacoes WHERE 1=1", []
    if somente_nao_lidas:
        sql += " AND lida=0"
    if tipo:
        sql += " AND tipo=?"; params.append(tipo)
    return paginar(sql + " ORDER BY criada_em DESC, id DESC", tuple(params), pagina, por_pagina)


def existe_nao_lida(tipo, produto_id):
    return scalar("SELECT COUNT(*) FROM notificacoes WHERE tipo=? AND produto_id=? AND lida=0", (tipo, produto_id)) > 0


def marcar_lida(id):
    execute("UPDATE notificacoes SET lida=1 WHERE id=?", (id,))


def marcar_todas_lidas():
    execute("UPDATE notificacoes SET lida=1 WHERE lida=0")
