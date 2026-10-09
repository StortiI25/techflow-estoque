"""Importa dados do banco do projeto antigo (database/estoqueflow.db) para o TechFlow Estoque.

Migra: usuários (hash de senha preservado - mesmo formato werkzeug), clientes e produtos
(categoria texto -> tabela categorias; estoque atual -> movimentação de entrada "estoque inicial").
NÃO migra o histórico antigo de movimentações/logs: ele não tem estoque anterior/posterior,
então não dá para reconstruir um histórico confiável. Guarde o arquivo antigo como arquivo morto.

Uso:  python -m database.migrar_legado caminho/estoqueflow.db
"""
import re
import sqlite3
import sys

from database.database import execute, query, scalar, transaction
from models import categoria
from services import auditoria_service, estoque_service


def _usuario_unico(base, usados):
    base = re.sub(r"[^a-z0-9._-]", "", base.lower())[:24] or "usuario"
    nome, n = base, 1
    while nome in usados or len(nome) < 3:
        n += 1
        nome = f"{base}{n}"
    usados.add(nome)
    return nome


def migrar(caminho):
    ant = sqlite3.connect(caminho)
    ant.row_factory = sqlite3.Row
    resumo = {"usuarios": 0, "clientes": 0, "produtos": 0, "ignorados": []}
    usados = {r["usuario"] for r in query("SELECT usuario FROM usuarios")}
    with transaction():
        for u in ant.execute("SELECT * FROM usuarios ORDER BY id"):
            if scalar("SELECT COUNT(*) FROM usuarios WHERE lower(email)=lower(?)", (u["email"],)):
                resumo["ignorados"].append(f"usuário {u['email']} (já existe)")
                continue
            perfil = u["perfil"] if u["perfil"] in ("admin", "funcionario", "visualizador") else "visualizador"
            login = _usuario_unico(u["usuario"] or u["email"].split("@")[0], usados)
            execute("INSERT INTO usuarios(nome,usuario,email,telefone,cargo,senha_hash,perfil,ativo) VALUES(?,?,?,?,?,?,?,?)",
                    (u["nome"], login, u["email"].lower(), u["telefone"], u["cargo"], u["senha"], perfil, 1 if u["ativo"] in (None, 1) else 0))
            resumo["usuarios"] += 1
        for c in ant.execute("SELECT * FROM clientes ORDER BY id"):
            execute("INSERT INTO clientes(nome,email,telefone,endereco) VALUES(?,?,?,?)", (c["nome"], c["email"], c["telefone"], c["endereco"]))
            resumo["clientes"] += 1
        admin = scalar("SELECT id FROM usuarios WHERE perfil='admin' AND ativo=1 ORDER BY id LIMIT 1")
        cats = {}
        for p in ant.execute("SELECT * FROM produtos ORDER BY id"):
            nome_cat = (p["categoria"] or "Outros").strip() or "Outros"
            if nome_cat not in cats:
                existente = query("SELECT id FROM categorias WHERE lower(nome)=lower(?)", (nome_cat,), one=True)
                cats[nome_cat] = existente["id"] if existente else categoria.criar({"nome": nome_cat, "descricao": ""})
            sku = f"LEG-{p['id']:04d}"
            barras = p["codigo_barras"] if p["codigo_barras"] and not scalar("SELECT COUNT(*) FROM produtos WHERE codigo_barras=?", (p["codigo_barras"],)) else None
            pid = execute("""INSERT INTO produtos(sku,codigo_barras,nome,categoria_id,preco_custo,preco_venda,estoque_atual,estoque_minimo,unidade)
                             VALUES(?,?,?,?,?,?,0,?,'unidade')""",
                          (sku, barras, p["nome"], cats[nome_cat], max(p["preco_custo"] or 0, 0), max(p["preco_venda"] or 0, 0), max(p["estoque_minimo"] or 0, 0))).lastrowid
            if (p["estoque"] or 0) > 0:
                estoque_service._aplicar(pid, "entrada", int(p["estoque"]), "outros", admin, observacao="Estoque inicial migrado do sistema antigo", silencioso=True)
            resumo["produtos"] += 1
        auditoria_service.registrar("Sistema", "migracao", None, f"Migração do sistema antigo: {resumo['usuarios']} usuários, {resumo['clientes']} clientes, {resumo['produtos']} produtos", admin)
    return resumo


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    from app import create_app
    app = create_app()
    with app.app_context():
        r = migrar(sys.argv[1])
    print(f"Migrado: {r['usuarios']} usuários, {r['clientes']} clientes, {r['produtos']} produtos.")
    for i in r["ignorados"]:
        print("  ignorado:", i)
