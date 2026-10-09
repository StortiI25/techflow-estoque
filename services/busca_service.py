from database.database import like, query


def buscar(termo, limite=8):
    termo = (termo or "").strip()
    if len(termo) < 2:
        return {"produtos": [], "categorias": [], "fornecedores": [], "clientes": []}
    t = like(termo)
    return {
        "produtos": query("""SELECT p.id, p.nome, p.sku, p.codigo_barras, p.estoque_atual, c.nome AS categoria
                             FROM produtos p JOIN categorias c ON c.id=p.categoria_id
                             WHERE p.nome LIKE ? ESCAPE '\\' OR p.sku LIKE ? ESCAPE '\\' OR p.codigo_barras LIKE ? ESCAPE '\\'
                             ORDER BY p.nome LIMIT ?""", (t, t, t, limite)),
        "categorias": query("SELECT id, nome, descricao FROM categorias WHERE nome LIKE ? ESCAPE '\\' ORDER BY nome LIMIT ?", (t, limite)),
        "fornecedores": query("""SELECT id, razao_social, nome_fantasia, cnpj, cidade FROM fornecedores
                                 WHERE razao_social LIKE ? ESCAPE '\\' OR nome_fantasia LIKE ? ESCAPE '\\' OR cnpj LIKE ? ESCAPE '\\'
                                 ORDER BY razao_social LIMIT ?""", (t, t, t, limite)),
        "clientes": query("""SELECT id, nome, documento, cidade FROM clientes
                             WHERE nome LIKE ? ESCAPE '\\' OR documento LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\'
                             ORDER BY nome LIMIT ?""", (t, t, t, limite)),
    }
