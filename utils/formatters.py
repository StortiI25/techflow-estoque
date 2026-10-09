from datetime import date, datetime

from utils.validators import so_digitos


def brl(valor):
    valor = float(valor or 0)
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def numero(valor):
    return f"{int(valor or 0):,}".replace(",", ".")


def data_br(valor, com_hora=True):
    if not valor:
        return "—"
    try:
        dt = datetime.strptime(str(valor)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt = datetime.strptime(str(valor)[:10], "%Y-%m-%d")
            com_hora = False
        except ValueError:
            return str(valor)
    return dt.strftime("%d/%m/%Y %H:%M" if com_hora else "%d/%m/%Y")


def documento(valor):
    d = so_digitos(valor)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return valor or "—"


def tempo_atras(valor):
    try:
        dt = datetime.strptime(str(valor)[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ""
    seg = int((datetime.now() - dt).total_seconds())
    if seg < 60:
        return "agora"
    if seg < 3600:
        return f"{seg // 60} min atrás"
    if seg < 86400:
        return f"{seg // 3600} h atrás"
    return f"{seg // 86400} d atrás"


def registrar_filtros(app):
    app.jinja_env.filters.update(brl=brl, numero=numero, data_br=data_br, documento=documento, tempo_atras=tempo_atras)


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_extenso(d=None):
    d = d or date.today()
    return f"{d.day} de {MESES[d.month - 1].capitalize()} de {d.year}"
