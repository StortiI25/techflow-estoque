from database.database import execute, query


def todas():
    return {r["chave"]: r["valor"] for r in query("SELECT chave, valor FROM configuracoes")}


def obter(chave, padrao=None):
    r = query("SELECT valor FROM configuracoes WHERE chave=?", (chave,), one=True)
    return r["valor"] if r else padrao


def definir(chave, valor):
    execute("""INSERT INTO configuracoes(chave,valor) VALUES(?,?)
               ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=datetime('now','localtime')""", (chave, str(valor)))
