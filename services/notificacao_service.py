"""Notificações persistidas (eventos) e alertas calculados na hora (estado atual do estoque)."""
from database.database import execute, query
from models import configuracao, notificacao

TIPOS = {
    "estoque_baixo": "Estoque baixo",
    "esgotado": "Estoque esgotado",
    "sem_movimentacao": "Sem movimentação",
    "entrada": "Entrada",
    "saida": "Saída",
    "sistema": "Sistema",
}


def avaliar_produto(produto_id):
    """Cria alerta de estoque baixo/esgotado (sem duplicar) ou resolve os pendentes se o estoque normalizou."""
    p = query("SELECT id, nome, sku, estoque_atual, estoque_minimo FROM produtos WHERE id=?", (produto_id,), one=True)
    if not p:
        return
    if p["estoque_atual"] <= 0:
        if not notificacao.existe_nao_lida("esgotado", p["id"]):
            notificacao.criar("esgotado", "Produto esgotado", f"{p['nome']} ({p['sku']}) está sem estoque.", p["id"])
    elif p["estoque_atual"] <= p["estoque_minimo"]:
        if not notificacao.existe_nao_lida("estoque_baixo", p["id"]):
            notificacao.criar("estoque_baixo", "Produto com estoque baixo",
                              f"{p['nome']} ({p['sku']}) - {p['estoque_atual']} un. (mínimo {p['estoque_minimo']}).", p["id"])
    else:
        execute("UPDATE notificacoes SET lida=1 WHERE produto_id=? AND tipo IN ('estoque_baixo','esgotado') AND lida=0", (p["id"],))


def avaliar_todos():
    for r in query("SELECT id FROM produtos WHERE ativo=1 AND estoque_atual<=estoque_minimo"):
        avaliar_produto(r["id"])


def alertas_ativos(limite=None):
    """Alertas calculados do estado atual (nunca ficam desatualizados)."""
    alertas = []
    for p in query("""SELECT id, nome, sku, estoque_atual, estoque_minimo FROM produtos
                      WHERE ativo=1 AND estoque_atual<=estoque_minimo ORDER BY estoque_atual, nome"""):
        if p["estoque_atual"] <= 0:
            alertas.append({"tipo": "esgotado", "nivel": "danger", "titulo": "Produto esgotado", "produto_id": p["id"],
                            "mensagem": f"{p['nome']} ({p['sku']}) está sem estoque."})
        else:
            alertas.append({"tipo": "estoque_baixo", "nivel": "warning", "titulo": "Produto com estoque baixo", "produto_id": p["id"],
                            "mensagem": f"{p['nome']} ({p['sku']}) - {p['estoque_atual']} un. (mínimo {p['estoque_minimo']})."})
    dias = int(configuracao.obter("dias_sem_movimentacao", "30") or 30)
    for p in produtos_sem_movimentacao(dias):
        alertas.append({"tipo": "sem_movimentacao", "nivel": "info", "titulo": "Produto sem movimentação", "produto_id": p["id"],
                        "mensagem": f"{p['nome']} ({p['sku']}) - {p['dias']} dias sem movimentação."})
    return alertas[:limite] if limite else alertas


def produtos_sem_movimentacao(dias):
    return query("""SELECT * FROM (
                      SELECT p.id, p.nome, p.sku, p.estoque_atual,
                             CAST(julianday('now','localtime') - julianday(COALESCE(
                                 (SELECT MAX(m.data_hora) FROM movimentacoes m WHERE m.produto_id=p.id), p.criado_em)) AS INTEGER) AS dias
                      FROM produtos p WHERE p.ativo=1 AND p.estoque_atual>0)
                    WHERE dias>=? ORDER BY dias DESC""", (dias,))
