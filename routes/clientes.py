from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from models import cliente
from services import auditoria_service
from utils.http import numero_pagina
from utils.security import login_obrigatorio, permissao
from utils.validators import ESTADOS

bp = Blueprint("clientes", __name__)


@bp.route("/clientes")
@login_obrigatorio
def lista():
    q = request.args.get("q", "").strip()
    return render_template("clientes/lista.html", pag=cliente.listar(q, numero_pagina(request.args), current_app.config["PER_PAGE"]), q=q)


@bp.route("/clientes/novo", methods=["GET", "POST"])
@permissao("cadastros")
def novo():
    dados, erros = {}, {}
    if request.method == "POST":
        dados, erros = cliente.validar(request.form)
        if not erros:
            cid = cliente.criar(dados)
            auditoria_service.registrar("Cadastro", "cliente", cid, f"Cliente cadastrado: {dados['nome']}")
            flash("Cliente cadastrado com sucesso.", "success")
            return redirect(url_for("clientes.detalhes", id=cid))
    return render_template("clientes/cadastro.html", c=None, dados=dados, erros=erros, estados=ESTADOS)


@bp.route("/clientes/<int:id>")
@login_obrigatorio
def detalhes(id):
    c = cliente.obter(id) or abort(404)
    return render_template("clientes/detalhes.html", c=c, d=cliente.detalhes(id))


@bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
@permissao("cadastros")
def editar(id):
    c = cliente.obter(id) or abort(404)
    dados, erros = dict(c), {}
    if request.method == "POST":
        dados, erros = cliente.validar(request.form, ignorar_id=id)
        if not erros:
            cliente.atualizar(id, dados)
            auditoria_service.registrar("Edição", "cliente", id, f"Cliente editado: {dados['nome']}")
            flash("Cliente atualizado com sucesso.", "success")
            return redirect(url_for("clientes.detalhes", id=id))
    return render_template("clientes/cadastro.html", c=c, dados=dados, erros=erros, estados=ESTADOS)


@bp.route("/clientes/<int:id>/status", methods=["POST"])
@permissao("cadastros")
def status(id):
    c = cliente.obter(id) or abort(404)
    cliente.definir_ativo(id, not c["ativo"])
    auditoria_service.registrar("Reativação" if not c["ativo"] else "Desativação", "cliente", id, c["nome"])
    flash("Cliente reativado." if not c["ativo"] else "Cliente desativado. O histórico foi preservado.", "success")
    return redirect(request.referrer or url_for("clientes.lista"))
