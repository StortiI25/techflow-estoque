from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from models import categoria, fornecedor, movimentacao, produto
from services import auditoria_service, estoque_service
from utils.http import filtros, numero_pagina
from utils.security import login_obrigatorio, permissao

bp = Blueprint("produtos", __name__)
CAMPOS_NUMERICOS = ("preco_custo", "preco_venda", "estoque_minimo", "estoque_maximo")


def _form_ctx(**extra):
    return dict(categorias=categoria.listar_ativas(), fornecedores=fornecedor.listar_ativos(), unidades=produto.UNIDADES, **extra)


def _obter_ou_404(id):
    p = produto.obter(id)
    if p is None:
        abort(404)
    return p


@bp.route("/produtos")
@login_obrigatorio
def lista():
    f = filtros(request.args, inteiros=("categoria_id", "fornecedor_id"))
    pag = produto.listar(f, numero_pagina(request.args), current_app.config["PER_PAGE"])
    return render_template("produtos/lista.html", pag=pag, f=f, categorias=categoria.listar_ativas(), fornecedores=fornecedor.listar_ativos())


@bp.route("/produtos/novo", methods=["GET", "POST"])
@permissao("cadastros")
def novo():
    dados, erros = {"unidade": "unidade", "quantidade_inicial": 0, "estoque_minimo": 0}, {}
    if request.method == "POST":
        limpos, erros = produto.validar(request.form, inclui_estoque_inicial=True)
        dados = {**limpos, **{k: request.form.get(k, "") for k in CAMPOS_NUMERICOS + ("quantidade_inicial",)}}
        imagem, erro_img = produto.salvar_imagem(request.files.get("imagem"), current_app.config["EXTENSOES_IMAGEM"], current_app.config["UPLOAD_FOLDER"])
        if erro_img:
            erros["imagem"] = erro_img
        if not erros:
            try:
                pid = estoque_service.cadastrar_produto(limpos, g.usuario["id"], imagem)
            except estoque_service.EstoqueError as e:
                flash(str(e), "danger")
            else:
                flash("Produto cadastrado com sucesso.", "success")
                return redirect(url_for("produtos.detalhes", id=pid))
    return render_template("produtos/cadastro.html", dados=dados, erros=erros, **_form_ctx())


@bp.route("/produtos/<int:id>")
@login_obrigatorio
def detalhes(id):
    p = _obter_ou_404(id)
    return render_template("produtos/detalhes.html", p=p, historico=movimentacao.do_produto(id, 30))


@bp.route("/produtos/<int:id>/editar", methods=["GET", "POST"])
@permissao("cadastros")
def editar(id):
    p = _obter_ou_404(id)
    dados, erros = dict(p), {}
    if request.method == "POST":
        limpos, erros = produto.validar(request.form, ignorar_id=id)
        dados = {**limpos, **{k: request.form.get(k, "") for k in CAMPOS_NUMERICOS}}
        imagem, erro_img = produto.salvar_imagem(request.files.get("imagem"), current_app.config["EXTENSOES_IMAGEM"], current_app.config["UPLOAD_FOLDER"])
        if erro_img:
            erros["imagem"] = erro_img
        if not erros:
            produto.atualizar(id, limpos, imagem)
            auditoria_service.registrar("Edição", "produto", id, f"Produto editado: {limpos['nome']} ({limpos['sku']})")
            flash("Produto atualizado com sucesso.", "success")
            return redirect(url_for("produtos.detalhes", id=id))
    return render_template("produtos/editar.html", p=p, dados=dados, erros=erros, **_form_ctx())


@bp.route("/produtos/<int:id>/status", methods=["POST"])
@permissao("cadastros")
def status(id):
    p = _obter_ou_404(id)
    novo_ativo = not p["ativo"]
    produto.definir_ativo(id, novo_ativo)
    auditoria_service.registrar("Reativação" if novo_ativo else "Desativação", "produto", id, f"{p['nome']} ({p['sku']})")
    flash("Produto reativado." if novo_ativo else "Produto desativado. O histórico foi preservado.", "success")
    return redirect(request.referrer or url_for("produtos.lista"))


@bp.route("/api/produtos/<int:id>")
@login_obrigatorio
def api_produto(id):
    p = _obter_ou_404(id)
    return jsonify({"id": p["id"], "nome": p["nome"], "sku": p["sku"], "estoque": p["estoque_atual"], "minimo": p["estoque_minimo"], "unidade": p["unidade"]})


@bp.route("/api/produtos/<int:id>/evolucao")
@login_obrigatorio
def api_evolucao(id):
    _obter_ou_404(id)
    return jsonify(produto.evolucao_estoque(id))
