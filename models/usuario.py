import re

from werkzeug.security import generate_password_hash

from database.database import execute, like, paginar, query, scalar
from utils.validators import email_valido, so_digitos

PERFIS_VALIDOS = ("admin", "funcionario", "visualizador")
SENHA_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def obter(id):
    return query("SELECT * FROM usuarios WHERE id=?", (id,), one=True)


def por_login(identificador):
    ident = (identificador or "").strip().lower()
    return query("SELECT * FROM usuarios WHERE lower(email)=? OR lower(usuario)=?", (ident, ident), one=True)


def listar(busca, pagina, por_pagina):
    sql, params = "SELECT * FROM usuarios WHERE 1=1", []
    if busca:
        sql += " AND (nome LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' OR usuario LIKE ? ESCAPE '\\')"
        params += [like(busca)] * 3
    return paginar(sql + " ORDER BY ativo DESC, nome", tuple(params), pagina, por_pagina)


def resumo():
    return {p: scalar("SELECT COUNT(*) FROM usuarios WHERE perfil=? AND ativo=1", (p,)) for p in PERFIS_VALIDOS}


def validar(form, ignorar_id=None, senha_obrigatoria=True, perfil_fixo=None):
    d = {k: (form.get(k) or "").strip() for k in ("nome", "usuario", "email", "telefone", "cargo")}
    d["email"] = d["email"].lower()
    d["usuario"] = d["usuario"].lower()
    d["perfil"] = perfil_fixo or form.get("perfil", "visualizador")
    senha, confirmar = form.get("senha", ""), form.get("confirmar_senha", "")
    e = {}
    if len(d["nome"].split()) < 2:
        e["nome"] = "Informe o nome completo."
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", d["usuario"]):
        e["usuario"] = "Use de 3 a 30 caracteres: letras, números, ponto, hífen ou sublinhado."
    if not email_valido(d["email"]):
        e["email"] = "Informe um e-mail válido."
    if d["telefone"] and len(so_digitos(d["telefone"])) < 10:
        e["telefone"] = "Informe o telefone com DDD."
    if d["perfil"] not in PERFIS_VALIDOS:
        e["perfil"] = "Perfil inválido."
    if senha or senha_obrigatoria:
        if not SENHA_RE.match(senha):
            e["senha"] = "Mínimo de 8 caracteres, com letra maiúscula, minúscula e número."
        elif senha != confirmar:
            e["confirmar_senha"] = "As senhas não coincidem."
    ig = ignorar_id or 0
    if "email" not in e and scalar("SELECT COUNT(*) FROM usuarios WHERE lower(email)=? AND id<>?", (d["email"], ig)):
        e["email"] = "Este e-mail já está cadastrado."
    if "usuario" not in e and scalar("SELECT COUNT(*) FROM usuarios WHERE lower(usuario)=? AND id<>?", (d["usuario"], ig)):
        e["usuario"] = "Este usuário já está em uso."
    d["senha"] = senha
    return d, e


def criar(d):
    cur = execute(
        "INSERT INTO usuarios(nome,usuario,email,telefone,cargo,senha_hash,perfil) VALUES(?,?,?,?,?,?,?)",
        (d["nome"], d["usuario"], d["email"], d["telefone"] or None, d["cargo"] or None,
         generate_password_hash(d["senha"]), d["perfil"]))
    return cur.lastrowid


def atualizar(id, d):
    execute("UPDATE usuarios SET nome=?,usuario=?,email=?,telefone=?,cargo=?,perfil=?,atualizado_em=datetime('now','localtime') WHERE id=?",
            (d["nome"], d["usuario"], d["email"], d["telefone"] or None, d["cargo"] or None, d["perfil"], id))
    if d.get("senha"):
        definir_senha(id, d["senha"])


def definir_senha(id, senha):
    execute("UPDATE usuarios SET senha_hash=?, atualizado_em=datetime('now','localtime') WHERE id=?",
            (generate_password_hash(senha), id))


def definir_ativo(id, ativo):
    execute("UPDATE usuarios SET ativo=?, atualizado_em=datetime('now','localtime') WHERE id=?", (1 if ativo else 0, id))


def registrar_login(id):
    execute("UPDATE usuarios SET ultimo_login=datetime('now','localtime') WHERE id=?", (id,))


def admins_ativos():
    return scalar("SELECT COUNT(*) FROM usuarios WHERE perfil='admin' AND ativo=1")
