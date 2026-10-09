"""Regras de negócio do estoque. É o ÚNICO lugar que altera produtos.estoque_atual."""
from database.database import execute, scalar, transaction
from models import movimentacao, notificacao, produto
from services import auditoria_service, notificacao_service

MOTIVOS_ENTRADA = ["compra", "devolução", "ajuste", "transferência", "produção", "outros"]
MOTIVOS_SAIDA = ["venda", "consumo interno", "perda", "avaria", "devolução", "transferência", "outros"]
MOTIVOS_AJUSTE = ["contagem de inventário", "correção de movimentação", "perda ou avaria identificada", "outros"]
MOTIVOS = {"entrada": MOTIVOS_ENTRADA, "saida": MOTIVOS_SAIDA, "ajuste": MOTIVOS_AJUSTE}
LIMITE_QUANTIDADE = 1_000_000


class EstoqueError(ValueError):
    """Erro de regra de negócio, com mensagem pronta para o usuário."""


def _inteiro_positivo(valor, rotulo="A quantidade"):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise EstoqueError(f"{rotulo} deve ser um número inteiro.")
    if n <= 0:
        raise EstoqueError(f"{rotulo} deve ser maior que zero.")
    if n > LIMITE_QUANTIDADE:
        raise EstoqueError(f"{rotulo} excede o limite permitido.")
    return n


def _validar_vinculos(cliente_id, fornecedor_id):
    if cliente_id and not scalar("SELECT COUNT(*) FROM clientes WHERE id=?", (cliente_id,)):
        raise EstoqueError("Cliente não encontrado.")
    if fornecedor_id and not scalar("SELECT COUNT(*) FROM fornecedores WHERE id=?", (fornecedor_id,)):
        raise EstoqueError("Fornecedor não encontrado.")


def _aplicar(produto_id, tipo, delta, motivo, usuario_id, cliente_id=None, fornecedor_id=None,
             observacao="", valor_unitario=None, data_hora=None, silencioso=False):
    """Núcleo: deve rodar dentro de uma transação. Aplica delta (+/-) e grava movimentação, auditoria e alertas."""
    p = produto.obter(produto_id)
    if p is None:
        raise EstoqueError("Produto não encontrado.")
    if not p["ativo"]:
        raise EstoqueError("Este produto está inativo e não pode ser movimentado.")
    anterior = p["estoque_atual"]
    posterior = anterior + delta
    if posterior < 0:
        un = "unidade" if anterior == 1 else "unidades"
        raise EstoqueError(f"Estoque insuficiente. Disponível: {anterior} {un}.")
    if valor_unitario is None:
        valor_unitario = p["preco_custo"] if tipo in ("entrada", "ajuste") else (p["preco_venda"] or p["preco_custo"])
    quantidade = abs(delta)
    execute("UPDATE produtos SET estoque_atual=?, atualizado_em=datetime('now','localtime') WHERE id=?", (posterior, produto_id))
    mov_id = movimentacao.inserir({
        "produto_id": produto_id, "usuario_id": usuario_id, "cliente_id": cliente_id or None, "fornecedor_id": fornecedor_id or None,
        "tipo": tipo, "motivo": motivo, "quantidade": quantidade, "estoque_anterior": anterior, "estoque_posterior": posterior,
        "valor_unitario": valor_unitario, "valor_total": round(valor_unitario * quantidade, 2),
        "observacao": observacao or None, "data_hora": data_hora})
    if not silencioso:
        rotulo = {"entrada": "Entrada", "saida": "Saída", "ajuste": "Ajuste"}[tipo]
        sinal = f"+{quantidade}" if delta > 0 else f"-{quantidade}"
        auditoria_service.registrar(rotulo, "movimentacao", mov_id,
                                    f"{p['nome']} ({p['sku']}): {anterior} → {posterior} ({sinal}) · {motivo}", usuario_id)
        notificacao.criar(tipo if tipo != "ajuste" else "sistema", f"{rotulo} registrada",
                          f"{p['nome']} - {sinal} {p['unidade']}", produto_id)
        notificacao_service.avaliar_produto(produto_id)
    avisos = []
    if delta > 0 and p["estoque_maximo"] and posterior > p["estoque_maximo"]:
        avisos.append(f"O estoque ({posterior}) passou do máximo definido ({p['estoque_maximo']}).")
    if posterior <= 0:
        avisos.append("Este produto está esgotado.")
    elif posterior <= p["estoque_minimo"]:
        avisos.append("Este produto está abaixo do estoque mínimo.")
    return {"id": mov_id, "produto": p, "anterior": anterior, "posterior": posterior, "avisos": avisos}


def registrar_entrada(produto_id, quantidade, motivo, usuario_id, fornecedor_id=None, observacao="", **kw):
    q = _inteiro_positivo(quantidade)
    if motivo not in MOTIVOS_ENTRADA:
        raise EstoqueError("Selecione um motivo válido para a entrada.")
    _validar_vinculos(None, fornecedor_id)
    with transaction():
        return _aplicar(produto_id, "entrada", q, motivo, usuario_id, fornecedor_id=fornecedor_id, observacao=observacao, **kw)


def registrar_saida(produto_id, quantidade, motivo, usuario_id, cliente_id=None, observacao="", **kw):
    q = _inteiro_positivo(quantidade)
    if motivo not in MOTIVOS_SAIDA:
        raise EstoqueError("Selecione um motivo válido para a saída.")
    _validar_vinculos(cliente_id, None)
    with transaction():
        return _aplicar(produto_id, "saida", -q, motivo, usuario_id, cliente_id=cliente_id, observacao=observacao, **kw)


def registrar_ajuste(produto_id, novo_estoque, motivo, usuario_id, observacao=""):
    """Define o saldo correto (contagem de inventário). Gera movimentação de ajuste com justificativa obrigatória."""
    try:
        novo = int(novo_estoque)
    except (TypeError, ValueError):
        raise EstoqueError("O novo estoque deve ser um número inteiro.")
    if novo < 0:
        raise EstoqueError("O estoque não pode ficar negativo.")
    if novo > LIMITE_QUANTIDADE:
        raise EstoqueError("O novo estoque excede o limite permitido.")
    if motivo not in MOTIVOS_AJUSTE:
        raise EstoqueError("Selecione um motivo válido para o ajuste.")
    if not (observacao or "").strip():
        raise EstoqueError("Informe a justificativa do ajuste na observação.")
    with transaction():
        atual = scalar("SELECT estoque_atual FROM produtos WHERE id=?", (produto_id,), padrao=None)
        if atual is None:
            raise EstoqueError("Produto não encontrado.")
        if novo == atual:
            raise EstoqueError("O novo estoque é igual ao estoque atual. Nada a ajustar.")
        return _aplicar(produto_id, "ajuste", novo - atual, motivo, usuario_id, observacao=observacao.strip())


def cadastrar_produto(dados, usuario_id, imagem=None):
    """Cria o produto e, se houver quantidade inicial, registra a entrada correspondente."""
    with transaction():
        pid = produto.inserir(dados, imagem)
        auditoria_service.registrar("Cadastro", "produto", pid, f"Produto cadastrado: {dados['nome']} ({dados['sku']})", usuario_id)
        qtd = dados.get("quantidade_inicial") or 0
        if qtd > 0:
            _aplicar(pid, "entrada", qtd, "outros", usuario_id, observacao="Estoque inicial no cadastro")
        else:
            notificacao_service.avaliar_produto(pid)
    return pid
