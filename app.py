"""TechFlow Estoque - fábrica da aplicação Flask (rotas em routes/, regras em services/)."""
import logging
import os

from flask import Flask, g, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from database.database import close_db, init_db
from models import configuracao, notificacao, usuario
from utils.formatters import data_extenso, registrar_filtros
from utils.security import PERFIS, csrf_token, pode, verificar_csrf


def url_pagina(numero):
    """URL da página atual preservando filtros da querystring (usado na paginação)."""
    args = {**(request.view_args or {}), **request.args.to_dict(), "page": numero}
    return url_for(request.endpoint, **args)


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    if app.config["PROXY_HOPS"] > 0:
        # O IP real do cliente é usado no bloqueio de login e na auditoria.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config["PROXY_HOPS"])
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.teardown_appcontext(close_db)
    registrar_filtros(app)
    app.jinja_env.globals.update(url_pagina=url_pagina, csrf_token=csrf_token)  # globais: visíveis dentro de macros importados
    _registrar_blueprints(app)
    _registrar_hooks(app)
    _registrar_erros(app)
    _registrar_cli(app)

    with app.app_context():
        init_db()  # idempotente (CREATE ... IF NOT EXISTS)
    return app


def _registrar_blueprints(app):
    from routes import (auth, categorias, clientes, dashboard, fornecedores, logs,
                        movimentacoes, notificacoes, produtos, relatorios, usuarios)
    for mod in (auth, dashboard, produtos, categorias, fornecedores, clientes, movimentacoes,
                relatorios, usuarios, notificacoes, logs):
        app.register_blueprint(mod.bp)


def _registrar_hooks(app):
    @app.before_request
    def carregar_usuario():
        g.usuario = None
        if request.endpoint == "static":
            return
        uid = session.get("usuario_id")
        if uid:
            u = usuario.obter(uid)
            if u and u["ativo"]:
                g.usuario = u
            else:  # conta removida/bloqueada: derruba a sessão na hora
                session.clear()
        verificar_csrf()

    @app.context_processor
    def contexto():
        dados = {"pode": pode, "csrf_token": csrf_token, "PERFIS": PERFIS, "versao": app.config["VERSAO"],
                 "usuario_logado": g.get("usuario"), "nome_empresa": "TechFlow Estoque"}
        dados["config_pub"] = configuracao.todas()
        dados["hoje_extenso"] = data_extenso()
        if g.get("usuario"):
            dados["notif_total"] = notificacao.nao_lidas()
            dados["notif_recentes"] = notificacao.recentes(5)
        return dados

    @app.after_request
    def cabecalhos(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if g.get("usuario"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp


def _registrar_erros(app):
    def pagina(codigo, titulo, mensagem):
        def handler(_e):
            return render_template(f"erros/{codigo}.html", titulo=titulo, mensagem=mensagem), codigo
        return handler

    app.register_error_handler(403, pagina(403, "Acesso negado", "Você não possui permissão para acessar esta página."))
    app.register_error_handler(404, pagina(404, "Página não encontrada", "O endereço acessado não existe ou foi removido."))
    app.register_error_handler(413, pagina(400, "Arquivo muito grande", "O arquivo enviado excede o limite de 2 MB."))

    def erro_400(e):
        msg = getattr(e, "description", None) or "Não foi possível processar a solicitação."
        return render_template("erros/400.html", titulo="Solicitação inválida", mensagem=msg), 400
    app.register_error_handler(400, erro_400)

    def erro_500(e):
        app.logger.exception("Erro interno: %s", e)
        try:
            close_db()
        except Exception:  # noqa: BLE001
            pass
        return render_template("erros/500.html", titulo="Erro interno",
                               mensagem="Algo deu errado do nosso lado. Tente novamente em instantes."), 500
    app.register_error_handler(500, erro_500)


def _registrar_cli(app):
    @app.cli.command("init-db")
    def init_db_cmd():
        init_db()
        print("Banco inicializado.")

    @app.cli.command("seed")
    def seed_cmd():
        from database.seed import executar
        executar()


_app = None


def __getattr__(nome):
    """Permite `gunicorn app:app` sem criar o banco só por importar o módulo (ex.: nos testes)."""
    global _app
    if nome == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(nome)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    aplicacao = create_app()
    with aplicacao.app_context():
        if not usuario.listar("", 1, 1)["total"]:
            print("Banco vazio. Gere os dados de demonstração com:  python -m database.seed")
    aplicacao.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
