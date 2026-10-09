from datetime import date, timedelta

from database.database import query, scalar


def indicadores():
    return {
        "total_produtos": scalar("SELECT COUNT(*) FROM produtos WHERE ativo=1"),
        "em_estoque": scalar("SELECT COUNT(*) FROM produtos WHERE ativo=1 AND estoque_atual>0"),
        "estoque_baixo": scalar("SELECT COUNT(*) FROM produtos WHERE ativo=1 AND estoque_atual>0 AND estoque_atual<=estoque_minimo"),
        "esgotados": scalar("SELECT COUNT(*) FROM produtos WHERE ativo=1 AND estoque_atual<=0"),
        "valor_estoque": scalar("SELECT SUM(estoque_atual*preco_custo) FROM produtos WHERE ativo=1", padrao=0),
        "valor_venda": scalar("SELECT SUM(estoque_atual*preco_venda) FROM produtos WHERE ativo=1", padrao=0),
        "novos_mes": scalar("SELECT COUNT(*) FROM produtos WHERE ativo=1 AND date(criado_em)>=date('now','localtime','start of month')"),
    }


def movimentos_por_dia(dias=7):
    dias = dias if dias in (7, 30, 90) else 7
    linhas = query("""SELECT date(data_hora) AS dia,
                             SUM(CASE WHEN estoque_posterior>estoque_anterior THEN estoque_posterior-estoque_anterior ELSE 0 END) AS entradas,
                             SUM(CASE WHEN estoque_posterior<estoque_anterior THEN estoque_anterior-estoque_posterior ELSE 0 END) AS saidas
                      FROM movimentacoes WHERE date(data_hora)>=date('now','localtime',?) GROUP BY dia""", (f"-{dias - 1} days",))
    por_dia = {r["dia"]: r for r in linhas}
    hoje = date.today()
    rotulos, entradas, saidas = [], [], []
    for i in range(dias - 1, -1, -1):
        d = hoje - timedelta(days=i)
        r = por_dia.get(d.isoformat())
        rotulos.append(d.strftime("%d/%m"))
        entradas.append(r["entradas"] if r else 0)
        saidas.append(r["saidas"] if r else 0)
    return {"rotulos": rotulos, "entradas": entradas, "saidas": saidas, "dias": dias}


def estoque_por_categoria():
    linhas = query("""SELECT c.nome, COUNT(p.id) AS produtos, COALESCE(SUM(p.estoque_atual),0) AS estoque
                      FROM categorias c JOIN produtos p ON p.categoria_id=c.id AND p.ativo=1
                      GROUP BY c.id ORDER BY produtos DESC, c.nome""")
    total = sum(r["produtos"] for r in linhas) or 1
    return [{"nome": r["nome"], "produtos": r["produtos"], "estoque": r["estoque"],
             "percentual": round(r["produtos"] * 100 / total)} for r in linhas]
