"""Registro de auditoria. Os logs são imutáveis (triggers no banco impedem UPDATE/DELETE)."""
from flask import has_request_context, request, session

from models import log


def registrar(acao, entidade=None, entidade_id=None, descricao="", usuario_id=None):
    if usuario_id is None and has_request_context():
        usuario_id = session.get("usuario_id")
    ip = request.remote_addr if has_request_context() else None
    log.inserir(usuario_id, acao, entidade, entidade_id, descricao, ip)
