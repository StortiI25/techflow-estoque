from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from models import configuracao, usuario
from services import auditoria_service
from utils.http import numero_pagina
from utils.security import PERFIS, permissao

bp = Blueprint("usuarios", __name__)


@bp.route("/usuarios")
@permissao("admin_usuarios")
def lista():
    q = request.args.get("q", "").strip()
    return render_template("usuarios/lista.html", pag=usuario.listar(q, numero_pagina(request.args), current_app.config["PER_PAGE"]),
                           q=q, resumo=usuario.resumo())


@bp.route("/usuarios/novo", methods=["GET", "POST"])
@permissao("admin_usuarios")
def novo():
    dados, erros = {"perfil": "funcionario"}, {}
    if request.method == "POST":
        dados, erros = usuario.validar(request.form)
        if not erros:
            uid = usuario.criar(dados)
            auditoria_service.registrar("Cadastro", "usuario", uid, f"Usuário criado: {dados['nome']} ({PERFIS[dados['perfil']]})")
            flash("Usuário cadastrado com sucesso.", "success")
            return redirect(url_for("usuarios.lista"))
    return render_template("usuarios/cadastro.html", dados=dados, erros=erros, perfis=PERFIS)


@bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@permissao("admin_usuarios")
def editar(id):
    u = usuario.obter(id) or abort(404)
    dados, erros = dict(u), {}
    if request.method == "POST":
        dados, erros = usuario.validar(request.form, ignorar_id=id, senha_obrigatoria=False)
        if not erros and u["perfil"] == "admin" and dados["perfil"] != "admin" and u["ativo"] and usuario.admins_ativos() <= 1:
            erros["perfil"] = "Não é possível rebaixar o único administrador ativo."
        if not erros:
            mudou_perfil = dados["perfil"] != u["perfil"]
            usuario.atualizar(id, dados)
            if mudou_perfil:
                auditoria_service.registrar("Alteração de permissão", "usuario", id,
                                            f"{u['nome']}: {PERFIS[u['perfil']]} → {PERFIS[dados['perfil']]}")
            auditoria_service.registrar("Alteração de usuário", "usuario", id,
                                        f"Dados de {dados['nome']} alterados" + (" (senha redefinida)" if dados["senha"] else ""))
            flash("Usuário atualizado com sucesso.", "success")
            return redirect(url_for("usuarios.lista"))
    return render_template("usuarios/editar.html", u=u, dados=dados, erros=erros, perfis=PERFIS)


@bp.route("/usuarios/<int:id>/status", methods=["POST"])
@permissao("admin_usuarios")
def status(id):
    u = usuario.obter(id) or abort(404)
    if u["id"] == g.usuario["id"]:
        flash("Você não pode bloquear a própria conta.", "warning")
    elif u["ativo"] and u["perfil"] == "admin" and usuario.admins_ativos() <= 1:
        flash("Não é possível bloquear o único administrador ativo.", "warning")
    else:
        usuario.definir_ativo(id, not u["ativo"])
        auditoria_service.registrar("Desativação" if u["ativo"] else "Reativação", "usuario", id, f"Usuário {u['nome']}")
        flash("Usuário bloqueado." if u["ativo"] else "Usuário desbloqueado.", "success")
    return redirect(url_for("usuarios.lista"))


@bp.route("/configuracoes", methods=["GET", "POST"])
@permissao("configuracoes")
def configuracoes():
    erros = {}
    cfg = configuracao.todas()
    if request.method == "POST":
        dias = request.form.get("dias_sem_movimentacao", "").strip()
        if not dias.isdigit() or not 1 <= int(dias) <= 365:
            erros["dias_sem_movimentacao"] = "Informe um número de dias entre 1 e 365."
        if not erros:
            novos = {"dias_sem_movimentacao": dias, "permitir_cadastro_publico": "1" if request.form.get("permitir_cadastro_publico") else "0"}
            alterados = [k for k, v in novos.items() if cfg.get(k) != v]
            for k, v in novos.items():
                configuracao.definir(k, v)
            if alterados:
                auditoria_service.registrar("Alteração de configuração", "configuracao", None, "Alterado: " + ", ".join(alterados))
            flash("Configurações salvas com sucesso.", "success")
            return redirect(url_for("usuarios.configuracoes"))
        cfg = {**cfg, **request.form.to_dict()}
    return render_template("configuracoes.html", cfg=cfg, erros=erros)
