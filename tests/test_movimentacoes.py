from tests.base import BaseTest


class TestAlertasHistoricoRelatorios(BaseTest):
    def setUp(self):
        super().setUp()
        self.login("admin")

    def mov(self, tipo, pid, qtd, motivo):
        return self.client.post(f"/movimentacoes/{tipo}/nova", data={"produto_id": pid, "quantidade": qtd, "motivo": motivo})

    # ---- Alertas
    def test_alerta_estoque_baixo_e_esgotado(self):
        self.novo_produto(sku="A", nome="Produto A", inicial=10, minimo=5)
        pid = self.produto_id("A")
        self.assertEqual(self.q("SELECT 1 FROM notificacoes WHERE tipo='estoque_baixo'"), [])
        self.mov("saida", pid, 5, "venda")   # 5 <= minimo 5 -> baixo
        self.assertEqual(len(self.q("SELECT 1 FROM notificacoes WHERE tipo='estoque_baixo' AND produto_id=?", (pid,))), 1)
        self.mov("saida", pid, 1, "venda")   # continua baixo: não duplica
        self.assertEqual(len(self.q("SELECT 1 FROM notificacoes WHERE tipo='estoque_baixo'")), 1)
        self.mov("saida", pid, 4, "venda")   # zerou
        self.assertEqual(len(self.q("SELECT 1 FROM notificacoes WHERE tipo='esgotado'")), 1)
        html = self.client.get("/alertas").get_data(as_text=True)
        self.assertIn("Produto esgotado", html)

    def test_alerta_some_quando_estoque_normaliza(self):
        self.novo_produto(sku="A", inicial=10, minimo=5)
        pid = self.produto_id("A")
        self.mov("saida", pid, 6, "venda")
        self.assertIn("estoque baixo", self.client.get("/alertas").get_data(as_text=True).lower())
        self.mov("entrada", pid, 50, "compra")
        self.assertEqual(self.q("SELECT 1 FROM notificacoes WHERE tipo IN ('estoque_baixo','esgotado') AND lida=0"), [])
        self.assertIn("Tudo em ordem", self.client.get("/alertas").get_data(as_text=True))

    def test_aviso_na_tela_ao_cair_abaixo_do_minimo(self):
        self.novo_produto(sku="A", inicial=10, minimo=5)
        r = self.client.post("/movimentacoes/saida/nova", data={"produto_id": self.produto_id("A"), "quantidade": 8, "motivo": "venda"}, follow_redirects=True)
        self.assertIn("abaixo do estoque mínimo", r.get_data(as_text=True))

    def test_marcar_como_lida(self):
        self.novo_produto(sku="A", inicial=2, minimo=5)
        self.assertGreater(len(self.q("SELECT 1 FROM notificacoes WHERE lida=0")), 0)
        self.client.post("/alertas/lidas")
        self.assertEqual(self.q("SELECT 1 FROM notificacoes WHERE lida=0"), [])

    def test_alerta_sem_movimentacao(self):
        from database.database import execute
        self.novo_produto(sku="A", nome="Parado", inicial=10, minimo=1)
        with self.app.app_context():
            execute("DROP TRIGGER mov_sem_update")
            execute("UPDATE movimentacoes SET data_hora=datetime('now','localtime','-45 days')")
        self.assertIn("45 dias sem movimentação", self.client.get("/alertas").get_data(as_text=True))

    # ---- Dashboard
    def test_dashboard_calculado_do_banco(self):
        self.novo_produto(sku="A", inicial=10, minimo=5, preco_custo="10.00")   # normal, 100
        self.novo_produto(sku="B", inicial=3, minimo=5, preco_custo="10.00")    # baixo, 30
        self.novo_produto(sku="C", inicial=0, minimo=5, preco_custo="10.00")    # esgotado
        from services import dashboard_service
        with self.app.app_context():
            k = dashboard_service.indicadores()
            self.assertEqual((k["total_produtos"], k["em_estoque"], k["estoque_baixo"], k["esgotados"]), (3, 2, 1, 1))
            self.assertEqual(k["valor_estoque"], 130)
            g = dashboard_service.movimentos_por_dia(7)
        self.assertEqual(len(g["rotulos"]), 7)
        self.assertEqual((g["entradas"][-1], g["saidas"][-1]), (13, 0))
        html = self.client.get("/dashboard").get_data(as_text=True)
        self.assertIn("R$ 130,00", html)
        j = self.client.get("/api/dashboard/movimentacoes?dias=30").get_json()
        self.assertEqual(len(j["rotulos"]), 30)
        self.assertEqual(self.client.get("/api/dashboard/movimentacoes?dias=abc").get_json()["dias"], 7)
        self.assertEqual(self.client.get("/api/dashboard/categorias").get_json()[0]["produtos"], 3)

    def test_dashboard_vazio_nao_quebra(self):
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Nenhuma movimentação ainda", r.get_data(as_text=True))

    # ---- Relatórios
    def test_relatorios_e_csv(self):
        self.novo_produto(sku="A", nome="Alpha", inicial=10, minimo=5)
        self.novo_produto(sku="B", nome="=HYPERLINK(\"x\")", inicial=2, minimo=5)
        pid = self.produto_id("A")
        self.mov("saida", pid, 3, "venda")
        for url in ("/relatorios", "/relatorios/estoque", "/relatorios/movimentacoes", "/relatorios/estoque-baixo"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        h = self.client.get("/relatorios/estoque-baixo").get_data(as_text=True)
        self.assertIn("-3", h)  # produto B: 2 - 5
        h = self.client.get("/relatorios/movimentacoes?tipo=saida").get_data(as_text=True)
        self.assertIn("-3", h)
        r = self.client.get("/relatorios/estoque?formato=csv")
        self.assertEqual(r.mimetype, "text/csv")
        txt = r.get_data(as_text=True)
        self.assertIn("Produto;SKU", txt)
        self.assertIn("Alpha", txt)
        self.assertIn("'=HYPERLINK", txt)           # neutraliza injeção de fórmula
        self.assertNotIn(";=HYPERLINK", txt)
        csv_mov = self.client.get("/relatorios/movimentacoes?formato=csv&tipo=saida").get_data(as_text=True)
        self.assertEqual(len(csv_mov.strip().splitlines()), 2)
        self.assertTrue(self.q("SELECT 1 FROM logs WHERE acao='Exportação'"))

    def test_totais_do_relatorio_de_movimentacoes(self):
        self.novo_produto(sku="A", inicial=10, minimo=1)
        pid = self.produto_id("A")
        self.mov("saida", pid, 4, "venda")
        from services import relatorio_service
        with self.app.app_context():
            d = relatorio_service.movimentacoes({})
        self.assertEqual((d["entradas"], d["saidas"], d["saldo"]), (10, 4, 6))
        self.assertEqual(d["valor_movimentado"], 10 * 10 + 4 * 20)

    # ---- Auditoria / cadastros
    def test_auditoria_visivel_ao_admin_com_ip(self):
        self.novo_produto(inicial=1)
        html = self.client.get("/auditoria").get_data(as_text=True)
        self.assertIn("Cadastro", html)
        self.assertTrue(self.q("SELECT 1 FROM logs WHERE ip IS NOT NULL"))

    def test_fornecedor_cnpj_e_cliente_cpf_validados(self):
        r = self.client.post("/fornecedores/novo", data={"razao_social": "X", "cnpj": "11.111.111/1111-11"})
        self.assertIn("CNPJ inválido", r.get_data(as_text=True))
        r = self.client.post("/fornecedores/novo", data={"razao_social": "X", "cnpj": "11.222.333/0001-81"})
        self.assertEqual(r.status_code, 302)
        r = self.client.post("/fornecedores/novo", data={"razao_social": "Y", "cnpj": "11222333000181"})
        self.assertIn("Já existe um fornecedor com este CNPJ", r.get_data(as_text=True))
        r = self.client.post("/clientes/novo", data={"nome": "Ana", "documento": "123.456.789-00"})
        self.assertIn("CPF ou CNPJ inválido", r.get_data(as_text=True))
        r = self.client.post("/clientes/novo", data={"nome": "Ana", "documento": "529.982.247-25", "email": "invalido"})
        self.assertIn("e-mail válido", r.get_data(as_text=True))
        r = self.client.post("/clientes/novo", data={"nome": "Ana", "documento": "529.982.247-25"})
        self.assertEqual(r.status_code, 302)

    def test_categoria_com_produtos_nao_desativa(self):
        self.novo_produto(inicial=1)
        r = self.client.post(f"/categorias/{self.cat}/status", follow_redirects=True)
        self.assertIn("existem produtos ativos", r.get_data(as_text=True))

    def test_todas_as_telas_renderizam(self):
        self.novo_produto(inicial=10)
        pid = self.produto_id()
        self.mov("saida", pid, 2, "venda")
        urls = ["/dashboard", "/produtos", "/produtos/novo", f"/produtos/{pid}", f"/produtos/{pid}/editar", "/categorias", "/categorias/nova", f"/categorias/{self.cat}/editar",
                "/fornecedores", "/fornecedores/novo", f"/fornecedores/{self.forn}", f"/fornecedores/{self.forn}/editar", "/clientes", "/clientes/novo", f"/clientes/{self.cli}",
                f"/clientes/{self.cli}/editar", "/movimentacoes", "/movimentacoes/entradas", "/movimentacoes/saidas", "/movimentacoes/entrada/nova", "/movimentacoes/saida/nova",
                f"/movimentacoes/ajuste/nova?produto_id={pid}", "/movimentacoes/2", "/relatorios", "/relatorios/estoque", "/relatorios/movimentacoes", "/relatorios/estoque-baixo",
                "/usuarios", "/usuarios/novo", f"/usuarios/{self.ids['funcionario']}/editar", "/alertas", "/auditoria", "/configuracoes", "/perfil", "/busca?q=mouse", "/busca?q="]
        for u in urls:
            r = self.client.get(u)
            self.assertEqual(r.status_code, 200, u)
            self.assertNotIn("Traceback", r.get_data(as_text=True), u)
