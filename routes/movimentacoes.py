from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from database.database import query
from models import cliente, fornecedor, movimentacao, produto
from services import estoque_service
from services.estoque_service import EstoqueError
from utils.http import filtros, numero_pagina
from utils.security import login_obrigatorio, permissao

bp = Blueprint("movimentacoes", __name__)
FILTROS_INT = ("produto_id", "usuario_id")
FILTROS_DATA = ("data_inicio", "data_fim")


def _listar(tipo, titulo):
    f = filtros(request.args, inteiros=FILTROS_INT, datas=FILTROS_DATA)
    if tipo:
        f["tipo"] = tipo
    pag = movimentacao.listar(f, numero_pagina(request.args), current_app.config["PER_PAGE"])
    return render_template("movimentacoes/lista.html", pag=pag, f=f, titulo=titulo, tipo_fixo=tipo,
                           produtos=produto.opcoes_movimentacao(), motivos=movimentacao.motivos_usados(),
                           usuarios=query("SELECT id, nome FROM usuarios ORDER BY nome"))


@bp.route("/movimentacoes")
@login_obrigatorio
def lista():
    return _listar(None, "Histórico de movimentações")


@bp.route("/movimentacoes/entradas")
@login_obrigatorio
def entradas():
    return _listar("entrada", "Entradas")


@bp.route("/movimentacoes/saidas")
@login_obrigatorio
def saidas():
    return _listar("saida", "Saídas")


@bp.route("/movimentacoes/<int:id>")
@login_obrigatorio
def detalhes(id):
    m = movimentacao.obter(id) or abort(404)
    return render_template("movimentacoes/detalhes.html", m=m)


def _int(valor):
    try:
        return int(valor) if valor not in (None, "") else None
    except ValueError:
        return None


def _processar(tipo, template, executar, extras):
    dados = {"produto_id": _int(request.args.get("produto_id"))}
    erro = None
    if request.method == "POST":
        dados = request.form.to_dict()
        dados["produto_id"] = _int(dados.get("produto_id"))
        try:
            r = executar(dados)
        except EstoqueError as e:
            erro = str(e)
        else:
            flash({"entrada": "Entrada registrada com sucesso.", "saida": "Saída registrada com sucesso.",
                   "ajuste": "Ajuste registrado com sucesso."}[tipo], "success")
            for aviso in r["avisos"]:
                flash(aviso, "warning")
            return redirect(url_for("produtos.detalhes", id=r["produto"]["id"]))
    return render_template(template, dados=dados, erro=erro, produtos=produto.opcoes_movimentacao(),
                           motivos=estoque_service.MOTIVOS[tipo], **extras)


@bp.route("/movimentacoes/entrada/nova", methods=["GET", "POST"])
@permissao("movimentar")
def nova_entrada():
    return _processar("entrada", "movimentacoes/entrada.html",
                      lambda d: estoque_service.registrar_entrada(d["produto_id"], d.get("quantidade"), d.get("motivo"), g.usuario["id"],
                                                                  _int(d.get("fornecedor_id")), (d.get("observacao") or "").strip()),
                      {"fornecedores": fornecedor.listar_ativos()})


@bp.route("/movimentacoes/saida/nova", methods=["GET", "POST"])
@permissao("movimentar")
def nova_saida():
    return _processar("saida", "movimentacoes/saida.html",
                      lambda d: estoque_service.registrar_saida(d["produto_id"], d.get("quantidade"), d.get("motivo"), g.usuario["id"],
                                                                _int(d.get("cliente_id")), (d.get("observacao") or "").strip()),
                      {"clientes": cliente.listar_ativos()})


@bp.route("/movimentacoes/ajuste/nova", methods=["GET", "POST"])
@permissao("ajustar")
def novo_ajuste():
    return _processar("ajuste", "movimentacoes/ajuste.html",
                      lambda d: estoque_service.registrar_ajuste(d["produto_id"], d.get("novo_estoque"), d.get("motivo"), g.usuario["id"],
                                                                 d.get("observacao") or ""), {})
