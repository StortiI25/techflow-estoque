"""Configurações do TechFlow Estoque (valores sensíveis vêm de variáveis de ambiente)."""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Em produção defina SECRET_KEY. Sem ela, uma chave temporária é gerada
    # a cada inicialização (as sessões deixam de valer ao reiniciar).
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DATABASE = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "database", "techflow.db"))
    PER_PAGE = 20
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB por upload
    EXTENSOES_IMAGEM = {"png", "jpg", "jpeg", "webp"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    CSRF_ENABLED = True
    # Quantos proxies reversos ficam entre o usuário e o app (Render = 1). Com 0, o cabeçalho
    # X-Forwarded-For é ignorado, o que evita que alguém forje o IP em ambiente sem proxy.
    PROXY_HOPS = int(os.getenv("PROXY_HOPS", "0") or 0)
    VERSAO = "1.0.0"
