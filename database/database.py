"""Camada de acesso ao banco. Todo o SQL passa por aqui (SQLite hoje; trocar o
driver neste módulo é o caminho para PostgreSQL, já que o schema usa SQL padrão)."""
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"], timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA.read_text(encoding="utf-8"))


def banco_inicializado():
    row = query("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'", one=True)
    return row is not None


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def scalar(sql, params=(), padrao=0):
    row = get_db().execute(sql, params).fetchone()
    return padrao if row is None or row[0] is None else row[0]


def execute(sql, params=()):
    return get_db().execute(sql, params)


@contextmanager
def transaction():
    """Transação com escrita imediata: leitura + validação + escrita ficam atômicas."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    else:
        db.execute("COMMIT")


def paginar(sql, params, pagina, por_pagina):
    total = scalar(f"SELECT COUNT(*) FROM ({sql})", params)
    paginas = max(1, math.ceil(total / por_pagina))
    pagina = min(max(1, pagina), paginas)
    itens = query(f"{sql} LIMIT ? OFFSET ?", (*params, por_pagina, (pagina - 1) * por_pagina))
    return {"itens": itens, "pagina": pagina, "paginas": paginas, "total": total, "por_pagina": por_pagina}


def like(termo):
    """Escapa curingas do LIKE (use com ESCAPE '\\')."""
    t = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{t}%"
