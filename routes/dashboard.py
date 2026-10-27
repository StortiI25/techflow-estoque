from flask import Blueprint, jsonify, render_template, request

from models import movimentacao, notificacao
from services import busca_service, dashboard_service, notificacao_service
from utils.security import login_obrigatorio

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_obrigatorio
def index():
    alertas = notificacao_service.alertas_ativos()
    return render_template(
        "dashboard.html",
        kpi=dashboard_service.indicadores(),
        alertas=alertas[:4],
        total_alertas=len(alertas),
        eventos=[n for n in notificacao.recentes(20) if n["tipo"] in ("entrada", "saida")][:3],
        movimentacoes=movimentacao.recentes(6),
        categorias=dashboard_service.estoque_por_categoria(),
    )


@bp.route("/api/dashboard/movimentacoes")
@login_obrigatorio
def api_movimentacoes():
    try:
        dias = int(request.args.get("dias", 7))
    except ValueError:
        dias = 7
    return jsonify(dashboard_service.movimentos_por_dia(dias))


@bp.route("/api/dashboard/categorias")
@login_obrigatorio
def api_categorias():
    return jsonify(dashboard_service.estoque_por_categoria())


@bp.route("/busca")
@login_obrigatorio
def busca():
    termo = request.args.get("q", "").strip()
    return render_template("busca.html", termo=termo, resultados=busca_service.buscar(termo))
