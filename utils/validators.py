import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ESTADOS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]


def so_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def email_valido(valor):
    return bool(EMAIL_RE.match(valor or ""))


def cpf_valido(valor):
    d = so_digitos(valor)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != int(d[n]):
            return False
    return True


def _dv_cnpj(base):
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(base) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    resto = sum(int(a) * b for a, b in zip(base, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_valido(valor):
    d = so_digitos(valor)
    if len(d) != 14 or d == d[0] * 14:
        return False
    return _dv_cnpj(d[:12]) == int(d[12]) and _dv_cnpj(d[:13]) == int(d[13])


def gerar_cnpj(base12):
    """Completa os dígitos verificadores (usado no seed de demonstração)."""
    d = so_digitos(base12)[:12]
    d += str(_dv_cnpj(d))
    d += str(_dv_cnpj(d))
    return d


def gerar_cpf(base9):
    d = so_digitos(base9)[:9]
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        d += str((soma * 10) % 11 % 10)
    return d


def parse_decimal(valor):
    """'1.234,56' ou '1234.56' -> float. Vazio -> None. Inválido -> ValueError."""
    v = (valor or "").strip().replace("R$", "").strip()
    if v == "":
        return None
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    return round(float(v), 2)


def parse_int(valor):
    v = (valor or "").strip()
    if v == "":
        return None
    return int(v)
