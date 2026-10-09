from datetime import datetime


def filtros(args, inteiros=(), datas=()):
    """Normaliza querystring: descarta valores vazios e números/datas inválidos (evita 500 com entrada maliciosa)."""
    f = {k: v.strip() for k, v in args.items() if v and v.strip() and k != "page"}
    for k in inteiros:
        if k in f and not f[k].isdigit():
            del f[k]
    for k in datas:
        if k in f:
            try:
                datetime.strptime(f[k], "%Y-%m-%d")
            except ValueError:
                del f[k]
    return f


def numero_pagina(args):
    try:
        return max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        return 1
