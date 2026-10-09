from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import categoria
from services import auditoria_service
from utils.security import login_obrigatorio, permissao

bp = Blueprint("categorias", __name__)


@bp.route("/categorias")
@login_obrigatorio
def lista():
    return render_template("categorias/lista.html", categorias=categoria.listar_com_resumo())


@bp.route("/categorias/nova", methods=["GET", "POST"])
@permissao("cadastros")
def nova():
    dados, erros = {}, {}
    if request.method == "POST":
        dados, erros = categoria.validar(request.form)
        if not erros:
            cid = categoria.criar(dados)
            auditoria_service.registrar("Cadastro", "categoria", cid, f"Categoria cadastrada: {dados['nome']}")
            flash("Categoria cadastrada com sucesso.", "success")
            return redirect(url_for("categorias.lista"))
    return render_template("categorias/cadastro.html", c=None, dados=dados, erros=erros)


@bp.route("/categorias/<int:id>/editar", methods=["GET", "POST"])
@permissao("cadastros")
def editar(id):
    c = categoria.obter(id) or abort(404)
    dados, erros = dict(c), {}
    if request.method == "POST":
        dados, erros = categoria.validar(request.form, ignorar_id=id)
        if not erros:
            categoria.atualizar(id, dados)
            auditoria_service.registrar("Edição", "categoria", id, f"Categoria editada: {dados['nome']}")
            flash("Categoria atualizada com sucesso.", "success")
            return redirect(url_for("categorias.lista"))
    return render_template("categorias/cadastro.html", c=c, dados=dados, erros=erros)


@bp.route("/categorias/<int:id>/status", methods=["POST"])
@permissao("cadastros")
def status(id):
    c = categoria.obter(id) or abort(404)
    if c["ativo"] and categoria.produtos_ativos(id):
        flash("Não é possível desativar: existem produtos ativos nesta categoria.", "warning")
        return redirect(url_for("categorias.lista"))
    categoria.definir_ativo(id, not c["ativo"])
    auditoria_service.registrar("Reativação" if not c["ativo"] else "Desativação", "categoria", id, c["nome"])
    flash("Categoria reativada." if not c["ativo"] else "Categoria desativada.", "success")
    return redirect(url_for("categorias.lista"))
