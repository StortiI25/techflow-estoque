from database.database import execute, query, scalar

RESUMO_SQL = """
SELECT c.*, COUNT(p.id) AS qtd_produtos,
       COALESCE(SUM(p.estoque_atual),0) AS qtd_estoque,
       COALESCE(SUM(p.estoque_atual*p.preco_custo),0) AS valor_total
FROM categorias c LEFT JOIN produtos p ON p.categoria_id=c.id AND p.ativo=1
GROUP BY c.id ORDER BY c.ativo DESC, c.nome
"""


def listar_com_resumo():
    return query(RESUMO_SQL)


def listar_ativas():
    return query("SELECT * FROM categorias WHERE ativo=1 ORDER BY nome")


def obter(id):
    return query("SELECT * FROM categorias WHERE id=?", (id,), one=True)


def validar(form, ignorar_id=None):
    d = {"nome": (form.get("nome") or "").strip(), "descricao": (form.get("descricao") or "").strip()}
    e = {}
    if not d["nome"]:
        e["nome"] = "O nome da categoria é obrigatório."
    elif scalar("SELECT COUNT(*) FROM categorias WHERE lower(nome)=lower(?) AND id<>?", (d["nome"], ignorar_id or 0)):
        e["nome"] = "Já existe uma categoria com este nome."
    return d, e


def criar(d):
    return execute("INSERT INTO categorias(nome,descricao) VALUES(?,?)", (d["nome"], d["descricao"] or None)).lastrowid


def atualizar(id, d):
    execute("UPDATE categorias SET nome=?, descricao=? WHERE id=?", (d["nome"], d["descricao"] or None, id))


def definir_ativo(id, ativo):
    execute("UPDATE categorias SET ativo=? WHERE id=?", (1 if ativo else 0, id))


def produtos_ativos(id):
    return scalar("SELECT COUNT(*) FROM produtos WHERE categoria_id=? AND ativo=1", (id,))
