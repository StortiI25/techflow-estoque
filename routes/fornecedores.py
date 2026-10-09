from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from models import fornecedor
from services import auditoria_service
from utils.http import numero_pagina
from utils.security import login_obrigatorio, permissao
from utils.validators import ESTADOS

bp = Blueprint("fornecedores", __name__)


@bp.route("/fornecedores")
@login_obrigatorio
def lista():
    q = request.args.get("q", "").strip()
    return render_template("fornecedores/lista.html", pag=fornecedor.listar(q, numero_pagina(request.args), current_app.config["PER_PAGE"]), q=q)


@bp.route("/fornecedores/novo", methods=["GET", "POST"])
@permissao("cadastros")
def novo():
    dados, erros = {}, {}
    if request.method == "POST":
        dados, erros = fornecedor.validar(request.form)
        if not erros:
            fid = fornecedor.criar(dados)
            auditoria_service.registrar("Cadastro", "fornecedor", fid, f"Fornecedor cadastrado: {dados['razao_social']}")
            flash("Fornecedor cadastrado com sucesso.", "success")
            return redirect(url_for("fornecedores.detalhes", id=fid))
    return render_template("fornecedores/cadastro.html", f=None, dados=dados, erros=erros, estados=ESTADOS)


@bp.route("/fornecedores/<int:id>")
@login_obrigatorio
def detalhes(id):
    f = fornecedor.obter(id) or abort(404)
    return render_template("fornecedores/detalhes.html", f=f, d=fornecedor.detalhes(id))


@bp.route("/fornecedores/<int:id>/editar", methods=["GET", "POST"])
@permissao("cadastros")
def editar(id):
    f = fornecedor.obter(id) or abort(404)
    dados, erros = dict(f), {}
    if request.method == "POST":
        dados, erros = fornecedor.validar(request.form, ignorar_id=id)
        if not erros:
            fornecedor.atualizar(id, dados)
            auditoria_service.registrar("Edição", "fornecedor", id, f"Fornecedor editado: {dados['razao_social']}")
            flash("Fornecedor atualizado com sucesso.", "success")
            return redirect(url_for("fornecedores.detalhes", id=id))
    return render_template("fornecedores/cadastro.html", f=f, dados=dados, erros=erros, estados=ESTADOS)


@bp.route("/fornecedores/<int:id>/status", methods=["POST"])
@permissao("cadastros")
def status(id):
    f = fornecedor.obter(id) or abort(404)
    fornecedor.definir_ativo(id, not f["ativo"])
    auditoria_service.registrar("Reativação" if not f["ativo"] else "Desativação", "fornecedor", id, f["razao_social"])
    flash("Fornecedor reativado." if not f["ativo"] else "Fornecedor desativado. O histórico foi preservado.", "success")
    return redirect(request.referrer or url_for("fornecedores.lista"))
