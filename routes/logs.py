from flask import Blueprint, render_template, request

from database.database import query
from models import log
from utils.http import filtros, numero_pagina
from utils.security import permissao

bp = Blueprint("logs", __name__)


@bp.route("/auditoria")
@permissao("auditoria")
def lista():
    f = filtros(request.args, inteiros=("usuario_id",), datas=("data_inicio", "data_fim"))
    pag = log.listar(f, numero_pagina(request.args), 30)
    return render_template("logs/lista.html", pag=pag, f=f, acoes=log.acoes(), usuarios=query("SELECT id, nome FROM usuarios ORDER BY nome"))
