from time import time

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import configuracao, usuario
from services import auditoria_service
from utils.security import destino_seguro, login_obrigatorio

bp = Blueprint("auth", __name__)
_falhas = {}
_HASH_FALSO = generate_password_hash("senha-inexistente")  # iguala o tempo de resposta quando o usuário não existe
MAX_TENTATIVAS, JANELA = 5, 600


def _bloqueado(ip):
    agora = time()
    recentes = [t for t in _falhas.get(ip, []) if agora - t < JANELA]
    _falhas[ip] = recentes
    return len(recentes) >= MAX_TENTATIVAS


@bp.route("/")
def inicio():
    return redirect(url_for("dashboard.index" if g.usuario else "auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("dashboard.index"))
    erro, ident = None, ""
    if request.method == "POST":
        ident, senha = request.form.get("identificador", "").strip(), request.form.get("senha", "")
        ip = request.remote_addr or "?"
        if not ident or not senha:
            erro = "Informe seu e-mail ou usuário e a senha."
        elif _bloqueado(ip):
            erro = "Muitas tentativas. Aguarde alguns minutos e tente novamente."
        else:
            u = usuario.por_login(ident)
            senha_ok = check_password_hash(u["senha_hash"] if u else _HASH_FALSO, senha)
            if u and senha_ok and u["ativo"]:
                session.clear()
                session["usuario_id"] = u["id"]
                session.permanent = bool(request.form.get("lembrar"))
                usuario.registrar_login(u["id"])
                auditoria_service.registrar("Login", "usuario", u["id"], f"Login realizado por {u['nome']}", u["id"])
                return redirect(destino_seguro(request.args.get("next")) or url_for("dashboard.index"))
            if u and senha_ok:
                erro = "Esta conta está bloqueada. Fale com o administrador."
            else:
                erro = "E-mail/usuário ou senha inválidos."
                _falhas.setdefault(ip, []).append(time())
                auditoria_service.registrar("Login falhou", "usuario", u["id"] if u else None,
                                            f"Tentativa de login inválida para '{ident[:60]}'", u["id"] if u else None)
    return render_template("login.html", erro=erro, identificador=ident), (401 if erro and request.method == "POST" else 200)


@bp.route("/logout", methods=["POST"])
@login_obrigatorio
def logout():
    auditoria_service.registrar("Logout", "usuario", g.usuario["id"], f"Logout de {g.usuario['nome']}")
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/esqueci-senha")
def esqueci_senha():
    return render_template("esqueci_senha.html")


@bp.route("/registrar", methods=["GET", "POST"])
def registrar():
    if configuracao.obter("permitir_cadastro_publico", "0") != "1":
        abort(404)
    if g.usuario:
        return redirect(url_for("dashboard.index"))
    dados, erros = {}, {}
    if request.method == "POST":
        dados, erros = usuario.validar(request.form, perfil_fixo="visualizador")
        if not request.form.get("aceite"):
            erros["aceite"] = "Aceite os termos de proteção de dados."
        if not erros:
            uid = usuario.criar(dados)
            auditoria_service.registrar("Cadastro", "usuario", uid, f"Auto-cadastro como visualizador: {dados['nome']}", uid)
            flash("Conta criada com sucesso. Faça login para acessar.", "success")
            return redirect(url_for("auth.login"))
    return render_template("registrar.html", dados=dados, erros=erros)


@bp.route("/perfil", methods=["GET", "POST"])
@login_obrigatorio
def perfil():
    u = g.usuario
    dados, erros = dict(u), {}
    if request.method == "POST":
        form = {"nome": request.form.get("nome"), "telefone": request.form.get("telefone"), "cargo": request.form.get("cargo"),
                "usuario": u["usuario"], "email": u["email"], "perfil": u["perfil"],
                "senha": request.form.get("senha_nova", ""), "confirmar_senha": request.form.get("confirmar_senha", "")}
        dados, erros = usuario.validar(form, ignorar_id=u["id"], senha_obrigatoria=False)
        if dados["senha"] and not check_password_hash(u["senha_hash"], request.form.get("senha_atual", "")):
            erros["senha_atual"] = "Senha atual incorreta."
        if not erros:
            usuario.atualizar(u["id"], dados)
            auditoria_service.registrar("Alteração de usuário", "usuario", u["id"],
                                        "Perfil atualizado" + (" (senha alterada)" if dados["senha"] else ""))
            flash("Perfil atualizado com sucesso.", "success")
            return redirect(url_for("auth.perfil"))
    return render_template("perfil.html", dados=dados, erros=erros)
