from flask import Blueprint, render_template, request

from database.database import query
from models import categoria, fornecedor, movimentacao, produto
from services import auditoria_service, relatorio_service
from utils.http import filtros, numero_pagina
from utils.security import permissao

bp = Blueprint("relatorios", __name__)
INTS = ("categoria_id", "fornecedor_id", "produto_id", "usuario_id")
DATAS = ("data_inicio", "data_fim")


def _exportar(nome, dados):
    auditoria_service.registrar("Exportação", "relatorio", None, f"Relatório '{nome}' exportado em CSV ({dados['total']} linhas)")
    return relatorio_service.FORMATOS["csv"][nome](dados)


@bp.route("/relatorios")
@permissao("relatorios")
def index():
    return render_template("relatorios/index.html")


@bp.route("/relatorios/estoque")
@permissao("relatorios")
def estoque():
    f = filtros(request.args, inteiros=INTS, datas=DATAS)
    f.pop("formato", None)
    if request.args.get("formato") == "csv":
        return _exportar("estoque", relatorio_service.estoque(f))
    dados = relatorio_service.estoque(f, numero_pagina(request.args), 25)
    return render_template("relatorios/estoque.html", d=dados, f=f, categorias=categoria.listar_ativas(), fornecedores=fornecedor.listar_ativos())


@bp.route("/relatorios/movimentacoes")
@permissao("relatorios")
def movimentacoes():
    f = filtros(request.args, inteiros=INTS, datas=DATAS)
    f.pop("formato", None)
    if request.args.get("formato") == "csv":
        return _exportar("movimentacoes", relatorio_service.movimentacoes(f))
    dados = relatorio_service.movimentacoes(f, numero_pagina(request.args), 25)
    return render_template("relatorios/movimentacoes.html", d=dados, f=f, produtos=produto.opcoes_movimentacao(),
                           motivos=movimentacao.motivos_usados(), usuarios=query("SELECT id, nome FROM usuarios ORDER BY nome"))


@bp.route("/relatorios/estoque-baixo")
@permissao("relatorios")
def estoque_baixo():
    if request.args.get("formato") == "csv":
        return _exportar("estoque_baixo", relatorio_service.estoque_baixo())
    return render_template("relatorios/estoque_baixo.html", d=relatorio_service.estoque_baixo(numero_pagina(request.args), 25))
