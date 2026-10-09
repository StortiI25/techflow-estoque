"""Relatórios e exportação. Para PDF, basta registrar um novo formato em FORMATOS (hoje só CSV)."""
import csv
import io

from flask import Response

from database.database import paginar, query
from models import movimentacao, produto


def _lista(sql, params, pagina, por_pagina):
    """Com pagina=None devolve tudo (exportação); caso contrário pagina no banco."""
    if pagina is None:
        itens = query(sql, tuple(params))
        return {"itens": itens, "total": len(itens)}
    return paginar(sql, tuple(params), pagina, por_pagina)


def _where_estoque(filtros):
    where, params = produto.filtrar(filtros)
    if filtros.get("data_inicio") or filtros.get("data_fim"):
        # "período" no relatório de estoque = produtos que tiveram movimentação no intervalo
        sub, p2 = "SELECT 1 FROM movimentacoes m WHERE m.produto_id=p.id", []
        if filtros.get("data_inicio"):
            sub += " AND date(m.data_hora)>=date(?)"; p2.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            sub += " AND date(m.data_hora)<=date(?)"; p2.append(filtros["data_fim"])
        where += f" AND EXISTS ({sub})"
        params += p2
    return where, params


def estoque(filtros, pagina=None, por_pagina=25):
    where, params = _where_estoque(filtros)
    dados = _lista(produto.BASE_SQL + where + " ORDER BY p.nome", params, pagina, por_pagina)
    tot = query("SELECT COALESCE(SUM(p.estoque_atual),0) AS qtd, COALESCE(SUM(p.estoque_atual*p.preco_custo),0) AS valor FROM produtos p" + where,
                tuple(params), one=True)
    dados.update(total_qtd=tot["qtd"], total_valor=tot["valor"])
    return dados


def movimentacoes(filtros, pagina=None, por_pagina=25):
    where, params = movimentacao.filtrar(filtros)
    dados = _lista(movimentacao.BASE_SQL + where + " ORDER BY m.data_hora DESC, m.id DESC", params, pagina, por_pagina)
    tot = query("""SELECT COALESCE(SUM(CASE WHEN m.estoque_posterior>m.estoque_anterior THEN m.estoque_posterior-m.estoque_anterior END),0) AS entradas,
                          COALESCE(SUM(CASE WHEN m.estoque_posterior<m.estoque_anterior THEN m.estoque_anterior-m.estoque_posterior END),0) AS saidas,
                          COALESCE(SUM(m.valor_total),0) AS valor
                   FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id""" + where, tuple(params), one=True)
    dados.update(entradas=tot["entradas"], saidas=tot["saidas"], saldo=tot["entradas"] - tot["saidas"], valor_movimentado=tot["valor"])
    return dados


def estoque_baixo(pagina=None, por_pagina=25):
    sql = produto.BASE_SQL + " WHERE p.ativo=1 AND p.estoque_atual<=p.estoque_minimo ORDER BY (p.estoque_atual-p.estoque_minimo), p.nome"
    return _lista(sql, [], pagina, por_pagina)


def _celula(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}".replace(".", ",")
    s = str(v)
    # evita injeção de fórmulas ao abrir o CSV no Excel/Sheets
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


def csv_response(nome_arquivo, cabecalho, linhas):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cabecalho)
    for l in linhas:
        w.writerow([_celula(c) for c in l])
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nome_arquivo}.csv"})


def csv_estoque(dados):
    cab = ["Produto", "SKU", "Categoria", "Fornecedor", "Estoque", "Preço de custo", "Valor total", "Status"]
    linhas = [[r["nome"], r["sku"], r["categoria"], r["fornecedor"], r["estoque_atual"], r["preco_custo"],
               round(r["estoque_atual"] * r["preco_custo"], 2), r["status"]] for r in dados["itens"]]
    return csv_response("relatorio_estoque", cab, linhas)


def csv_movimentacoes(dados):
    cab = ["Data", "Produto", "SKU", "Tipo", "Motivo", "Quantidade", "Estoque anterior", "Estoque posterior", "Valor total", "Usuário", "Cliente", "Fornecedor"]
    linhas = [[r["data_hora"], r["produto"], r["sku"], r["tipo"], r["motivo"], r["delta"], r["estoque_anterior"], r["estoque_posterior"],
               r["valor_total"], r["usuario"], r["cliente"], r["fornecedor"]] for r in dados["itens"]]
    return csv_response("relatorio_movimentacoes", cab, linhas)


def csv_estoque_baixo(dados):
    cab = ["Produto", "SKU", "Estoque atual", "Estoque mínimo", "Diferença", "Status"]
    linhas = [[r["nome"], r["sku"], r["estoque_atual"], r["estoque_minimo"], r["estoque_atual"] - r["estoque_minimo"], r["status"]] for r in dados["itens"]]
    return csv_response("relatorio_estoque_baixo", cab, linhas)


FORMATOS = {"csv": {"estoque": csv_estoque, "movimentacoes": csv_movimentacoes, "estoque_baixo": csv_estoque_baixo}}
