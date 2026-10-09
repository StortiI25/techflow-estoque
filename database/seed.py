"""DADOS DE DEMONSTRAÇÃO do TechFlow Estoque.

Tudo aqui é fictício (empresas, CNPJs gerados, clientes, produtos e movimentações) e serve
apenas para demonstrar o sistema. NÃO use estas senhas em produção.

Uso:  python -m database.seed            (banco vazio)
      python -m database.seed --reset    (apaga o banco atual e recria)
"""
import os
import random
import sys
from datetime import datetime, timedelta

from database.database import init_db, scalar, transaction
from models import categoria, cliente, fornecedor, usuario
from services import auditoria_service, estoque_service, notificacao_service
from utils.validators import gerar_cnpj, gerar_cpf

USUARIOS_DEMO = [
    # nome, usuario, email, senha, perfil, cargo
    ("Carlos Henrique", "carlos", "admin@techflow.com", "Admin@123", "admin", "Gerente de Estoque"),
    ("João Silva", "joao", "funcionario@techflow.com", "Func@123", "funcionario", "Almoxarife"),
    ("Maria Oliveira", "maria", "visualizador@techflow.com", "Visu@123", "visualizador", "Analista"),
]
CATEGORIAS = ["Informática", "Eletrônicos", "Periféricos", "Escritório", "Ferramentas", "Materiais"]
FORNECEDORES = [("Distribuidora ABC Ltda", "ABC Distribuidora", "Campinas", "SP"), ("Tech Import S.A.", "TechImport", "São Paulo", "SP"),
                ("Papelaria Central Ltda", "Papelaria Central", "Curitiba", "PR"), ("Ferramentas Brasil Ltda", "FerraBR", "Belo Horizonte", "MG"),
                ("Eletro Sul Comércio Ltda", "Eletro Sul", "Porto Alegre", "RS")]
CLIENTES = [("Empresa XYZ Ltda", "Santos", "SP"), ("Mercado Central", "São Paulo", "SP"), ("TechNova Soluções", "Campinas", "SP"),
            ("Alpha Distribuidora", "Guarulhos", "SP"), ("Loja Prime Imports", "Santos", "SP"), ("Digital Max Comércio", "Sorocaba", "SP"),
            ("Ana Paula Ribeiro", "Diadema", "SP"), ("Escola Futuro Brilhante", "São Bernardo do Campo", "SP")]
# nome, categoria, fornecedor(idx), custo, venda, minimo, maximo, unidade
PRODUTOS = [
    ("Notebook 15\" Core i5", 0, 1, 2800, 3699.9, 5, 40, "unidade"), ("Notebook 14\" Ryzen 5", 0, 1, 2600, 3399.9, 5, 40, "unidade"),
    ("SSD 1TB NVMe", 0, 1, 320, 479.9, 10, 120, "unidade"), ("Memória RAM 16GB DDR4", 0, 1, 210, 319.9, 10, 120, "unidade"),
    ("Placa de rede Wi-Fi 6", 0, 1, 70, 119.9, 8, 80, "unidade"), ("Roteador Wi-Fi AX1800", 0, 4, 190, 289.9, 8, 60, "unidade"),
    ("Switch 8 portas Gigabit", 0, 4, 110, 169.9, 6, 50, "unidade"), ("Cabo de rede Cat6 (caixa 305m)", 0, 4, 480, 690, 3, 20, "caixa"),
    ("Mouse Wireless", 2, 1, 38, 69.9, 20, 200, "unidade"), ("Teclado USB ABNT2", 2, 1, 32, 59.9, 20, 200, "unidade"),
    ("Teclado Mecânico RGB", 2, 1, 150, 249.9, 10, 80, "unidade"), ("Headset USB com microfone", 2, 1, 85, 139.9, 10, 90, "unidade"),
    ("Webcam Full HD", 2, 1, 95, 159.9, 8, 70, "unidade"), ("Mousepad grande", 2, 2, 14, 29.9, 15, 150, "unidade"),
    ("Monitor 24\" Full HD", 1, 4, 620, 899.9, 6, 50, "unidade"), ("Monitor 27\" 2K", 1, 4, 980, 1399.9, 4, 30, "unidade"),
    ("Smart TV 43\"", 1, 4, 1450, 1999.9, 3, 25, "unidade"), ("Caixa de som Bluetooth", 1, 4, 120, 199.9, 10, 80, "unidade"),
    ("Carregador USB-C 65W", 1, 4, 55, 99.9, 15, 120, "unidade"), ("Cabo HDMI 2m", 1, 1, 12, 24.9, 30, 300, "unidade"),
    ("Pilhas AA (pacote 4)", 1, 4, 8, 15.9, 40, 400, "pacote"), ("Papel A4 (resma 500 folhas)", 3, 2, 22, 32.9, 30, 300, "pacote"),
    ("Caneta esferográfica azul (caixa 50)", 3, 2, 28, 44.9, 10, 100, "caixa"), ("Grampeador de mesa", 3, 2, 18, 32.9, 8, 60, "unidade"),
    ("Pasta suspensa (pacote 25)", 3, 2, 36, 59.9, 6, 60, "pacote"), ("Bloco de notas adesivas", 3, 2, 5, 11.9, 30, 300, "unidade"),
    ("Cadeira de escritório ergonômica", 3, 2, 420, 649.9, 3, 25, "unidade"), ("Etiquetas adesivas (rolo)", 3, 2, 9, 17.9, 20, 200, "unidade"),
    ("Furadeira de impacto 650W", 4, 3, 190, 289.9, 4, 30, "unidade"), ("Jogo de chaves Phillips/fenda (12 pç)", 4, 3, 35, 64.9, 8, 60, "unidade"),
    ("Alicate universal 8\"", 4, 3, 22, 41.9, 10, 80, "unidade"), ("Trena 5m", 4, 3, 12, 22.9, 15, 120, "unidade"),
    ("Parafusadeira a bateria 12V", 4, 3, 160, 249.9, 4, 30, "unidade"), ("Multímetro digital", 4, 3, 48, 84.9, 6, 50, "unidade"),
    ("Fita isolante (rolo)", 5, 3, 3.5, 7.9, 40, 500, "unidade"), ("Abraçadeira de nylon (pacote 100)", 5, 3, 9, 16.9, 25, 250, "pacote"),
    ("Fita dupla face (rolo)", 5, 2, 7, 13.9, 25, 250, "unidade"), ("Fio flexível 2,5mm (rolo 100m)", 5, 3, 210, 319.9, 3, 25, "unidade"),
    ("Parafuso 5mm (caixa 500)", 5, 3, 24, 39.9, 10, 100, "caixa"), ("Cola instantânea 20g", 5, 2, 4, 9.9, 30, 300, "unidade"),
    ("Pen drive 64GB", 0, 1, 24, 44.9, 20, 200, "unidade"), ("HD externo 1TB", 0, 1, 280, 399.9, 6, 50, "unidade"),
]
DORMENTES = {37, 38}   # produtos que ficam sem movimentação (geram alerta "sem movimentação")
BAIXOS = {3, 8, 14, 19, 22, 30, 33}
ESGOTADOS = {5, 17, 28}


def _cpf_cnpj(i):
    return gerar_cnpj(f"{11000000 + i * 137:08d}0001") if i % 2 == 0 else gerar_cpf(f"{123456000 + i * 7919:09d}"[:9])


def executar(reset=False):
    from flask import current_app
    caminho = current_app.config["DATABASE"]
    if reset:
        from database.database import close_db
        close_db()
        if os.path.exists(caminho):
            os.remove(caminho)
        init_db()
    if scalar("SELECT COUNT(*) FROM usuarios"):
        print("O banco já possui dados. Use --reset para recriar.")
        return
    rnd = random.Random(42)  # determinístico: mesma demonstração sempre

    ids_usuario = {}
    for nome, login, email, senha, perfil, cargo in USUARIOS_DEMO:
        ids_usuario[perfil] = usuario.criar({"nome": nome, "usuario": login, "email": email, "telefone": "11999990000", "cargo": cargo, "senha": senha, "perfil": perfil})
    admin, func = ids_usuario["admin"], ids_usuario["funcionario"]

    cat_ids = [categoria.criar({"nome": n, "descricao": f"Produtos de {n.lower()}"}) for n in CATEGORIAS]
    forn_ids = []
    for i, (rs, nf, cidade, uf) in enumerate(FORNECEDORES):
        forn_ids.append(fornecedor.criar({"razao_social": rs, "nome_fantasia": nf, "cnpj": gerar_cnpj(f"{22000000 + i * 991:08d}0001"),
                                          "email": f"contato@{nf.lower().replace(' ', '')}.com.br", "telefone": "1130001000", "endereco": "Av. Exemplo, 1000",
                                          "cidade": cidade, "estado": uf, "observacoes": "Fornecedor de demonstração"}))
    cli_ids = []
    for i, (nome, cidade, uf) in enumerate(CLIENTES):
        cli_ids.append(cliente.criar({"nome": nome, "documento": _cpf_cnpj(i), "email": f"compras{i}@exemplo.com.br", "telefone": "11988887777",
                                      "endereco": "Rua Exemplo, 100", "cidade": cidade, "estado": uf}))

    from models import produto
    prod_ids = []
    with transaction():
        for i, (nome, ci, fi, custo, venda, minimo, maximo, un) in enumerate(PRODUTOS):
            prod_ids.append(produto.inserir({"sku": f"TF-{i + 1:04d}", "codigo_barras": f"789{1000000000 + i * 37:010d}", "nome": nome, "descricao": f"{nome} (produto de demonstração)",
                                             "categoria_id": cat_ids[ci], "fornecedor_id": forn_ids[fi], "preco_custo": custo, "preco_venda": venda,
                                             "estoque_minimo": minimo, "estoque_maximo": maximo, "unidade": un}))

    hoje = datetime.now().replace(second=0, microsecond=0)

    contagem = {}

    def momento(dias_atras):
        """Horários crescentes dentro do dia (histórico coerente: estoque anterior = posterior da movimentação anterior)."""
        n = contagem.get(dias_atras, 0)
        contagem[dias_atras] = n + 1
        base = hoje.replace(hour=0, minute=10) if dias_atras == 0 else hoje.replace(hour=8, minute=0)
        return (base - timedelta(days=dias_atras) + timedelta(minutes=(2 * n if dias_atras == 0 else n * 17 + rnd.randint(0, 9)))).strftime("%Y-%m-%d %H:%M:%S")

    def mov(i, tipo, qtd, dias, motivo, usuario_id):
        pid = prod_ids[i]
        kw = dict(data_hora=momento(dias), silencioso=True)
        with transaction():
            if tipo == "entrada":
                estoque_service._aplicar(pid, "entrada", qtd, motivo, usuario_id, fornecedor_id=forn_ids[PRODUTOS[i][2]], **kw)
            else:
                estoque_service._aplicar(pid, "saida", -qtd, motivo, usuario_id, cliente_id=rnd.choice(cli_ids) if motivo == "venda" else None, **kw)

    estoque = {}
    for i, p in enumerate(PRODUTOS):                         # carga inicial (compra) há 60 dias (dormentes: 55)
        q = rnd.randint(p[5] * 3, max(p[5] * 6, p[5] * 3 + 1))
        mov(i, "entrada", q, 55 if i in DORMENTES else 60, "compra", admin)
        estoque[i] = q
    ativos = [i for i in range(len(PRODUTOS)) if i not in DORMENTES]
    # metas finais: esgotados em 0, baixos um pouco abaixo/no mínimo, demais acima do mínimo
    alvo = {i: 0 if i in ESGOTADOS else max(1, PRODUTOS[i][5] - rnd.randint(0, 2)) for i in BAIXOS | ESGOTADOS}
    for dia in range(59, -1, -1):                            # 60 dias de movimento
        for _ in range(rnd.randint(2, 7)):
            livres = [i for i in ativos if not (dia <= 8 and i in alvo)]   # nos últimos dias, baixos/esgotados só descem
            i = rnd.choice(livres)
            quem = rnd.choice([admin, func])
            if rnd.random() < 0.62 and estoque[i] > 2:
                q = rnd.randint(1, max(1, min(estoque[i] - 1, PRODUTOS[i][5] + 6)))
                mov(i, "saida", q, dia, rnd.choice(["venda"] * 6 + ["consumo interno", "perda", "avaria"]), quem)
                estoque[i] -= q
            else:
                q = rnd.randint(PRODUTOS[i][5], PRODUTOS[i][5] * 3)
                mov(i, "entrada", q, dia, rnd.choice(["compra"] * 5 + ["devolução", "transferência"]), quem)
                estoque[i] += q
        if dia <= 8:                                         # descida gradual até a meta (sem concentrar tudo em um dia)
            for i, meta in alvo.items():
                if estoque[i] > meta:
                    q = -(-(estoque[i] - meta) // (dia + 1))
                    mov(i, "saida", q, dia, "venda", func)
                    estoque[i] -= q
    for i in range(len(PRODUTOS)):                           # demais produtos terminam acima do mínimo
        if i not in DORMENTES and i not in alvo and estoque[i] < PRODUTOS[i][5] + 5:
            mov(i, "entrada", PRODUTOS[i][5] + 5 - estoque[i], 0, "compra", admin)
            estoque[i] = PRODUTOS[i][5] + 5

    notificacao_service.avaliar_todos()
    auditoria_service.registrar("Sistema", "sistema", None, "Dados de demonstração gerados (seed)", admin)
    print("\nDados de demonstração criados.")
    print(f"{len(PRODUTOS)} produtos · {len(CATEGORIAS)} categorias · {len(FORNECEDORES)} fornecedores · {len(CLIENTES)} clientes · {scalar('SELECT COUNT(*) FROM movimentacoes')} movimentações")
    print("\nUsuários de demonstração:")
    for nome, login, email, senha, perfil, _ in USUARIOS_DEMO:
        print(f"  {perfil:<13} {email:<28} senha: {senha}")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        executar(reset="--reset" in sys.argv)
