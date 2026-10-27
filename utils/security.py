"""Autenticação, permissões (RBAC) e proteção CSRF."""
import hmac
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import abort, current_app, g, redirect, request, session, url_for

PERMISSOES = {
    "admin": {"*"},
    "funcionario": {"ver", "movimentar", "relatorios"},
    "visualizador": {"ver", "relatorios"},
}
PERFIS = {"admin": "Administrador", "funcionario": "Funcionário", "visualizador": "Visualizador"}


def pode(permissao):
    usuario = g.get("usuario")
    if not usuario:
        return False
    permitidas = PERMISSOES.get(usuario["perfil"], set())
    return "*" in permitidas or permissao in permitidas


def login_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.get("usuario"):
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)
    return wrapper


def permissao(nome):
    """Exige login + permissão no backend (não depende de esconder botões)."""
    def decorador(view):
        @wraps(view)
        @login_obrigatorio
        def wrapper(*args, **kwargs):
            if not pode(nome):
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorador


def destino_seguro(destino):
    if not destino:
        return None
    p = urlparse(destino)
    return destino if not p.netloc and not p.scheme and destino.startswith("/") and not destino.startswith("//") else None


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def verificar_csrf():
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        enviado = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
        esperado = session.get("_csrf", "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            abort(400, description="Sessão expirada ou formulário inválido. Recarregue a página e tente novamente.")
