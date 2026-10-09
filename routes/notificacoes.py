from flask import Blueprint, current_app, redirect, render_template, request, url_for

from models import notificacao
from services import notificacao_service
from utils.http import numero_pagina
from utils.security import login_obrigatorio

bp = Blueprint("notificacoes", __name__)


@bp.route("/alertas")
@login_obrigatorio
def lista():
    nao_lidas = request.args.get("somente") == "nao_lidas"
    tipo = request.args.get("tipo") if request.args.get("tipo") in notificacao_service.TIPOS else None
    pag = notificacao.listar(nao_lidas, tipo, numero_pagina(request.args), current_app.config["PER_PAGE"])
    return render_template("notificacoes/lista.html", alertas=notificacao_service.alertas_ativos(), pag=pag,
                           tipos=notificacao_service.TIPOS, tipo=tipo, nao_lidas=nao_lidas)


@bp.route("/alertas/<int:id>/lida", methods=["POST"])
@login_obrigatorio
def marcar_lida(id):
    notificacao.marcar_lida(id)
    return redirect(request.referrer or url_for("notificacoes.lista"))


@bp.route("/alertas/lidas", methods=["POST"])
@login_obrigatorio
def marcar_todas():
    notificacao.marcar_todas_lidas()
    return redirect(request.referrer or url_for("notificacoes.lista"))
