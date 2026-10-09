from tests.base import BaseTest


class TestProdutos(BaseTest):
    def setUp(self):
        super().setUp()
        self.login("admin")

    def test_cadastro_com_estoque_inicial_gera_movimentacao(self):
        r = self.novo_produto(inicial=20)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.estoque(), 20)
        movs = self.q("SELECT tipo, quantidade, estoque_anterior, estoque_posterior FROM movimentacoes")
        self.assertEqual(movs, [{"tipo": "entrada", "quantidade": 20, "estoque_anterior": 0, "estoque_posterior": 20}])
        self.assertTrue(self.q("SELECT 1 FROM logs WHERE acao='Cadastro' AND entidade='produto'"))

    def test_sku_duplicado_bloqueado(self):
        self.novo_produto(sku="ABC")
        r = self.novo_produto(sku="abc", nome="Outro")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Já existe um produto com este SKU", r.get_data(as_text=True))
        self.assertEqual(len(self.q("SELECT 1 FROM produtos")), 1)

    def test_codigo_de_barras_duplicado_bloqueado(self):
        self.novo_produto(sku="A", codigo_barras="789000")
        r = self.novo_produto(sku="B", codigo_barras="789000")
        self.assertIn("código de barras", r.get_data(as_text=True))

    def test_validacoes_de_campos(self):
        casos = [({"nome": ""}, "nome do produto é obrigatório"), ({"sku": ""}, "SKU é obrigatório"), ({"preco_custo": "-1"}, "não pode ser negativo"),
                 ({"estoque_minimo": "-3"}, "não pode ser negativo"), ({"quantidade_inicial": "-5"}, "não pode ser negativo"),
                 ({"preco_custo": "abc"}, "valor numérico"), ({"categoria_id": ""}, "categoria válida")]
        for i, (alt, msg) in enumerate(casos):
            dados = {"nome": "P", "sku": f"S{i}", "categoria_id": self.cat, "preco_custo": "1", "estoque_minimo": "1", "unidade": "unidade", **alt}
            r = self.client.post("/produtos/novo", data=dados)
            self.assertEqual(r.status_code, 200, alt)
            self.assertIn(msg, r.get_data(as_text=True), alt)
        self.assertEqual(self.q("SELECT 1 FROM produtos"), [])

    def test_edicao_nao_altera_estoque(self):
        self.novo_produto(inicial=10)
        pid = self.produto_id()
        r = self.client.post(f"/produtos/{pid}/editar", data={"nome": "Mouse Novo", "sku": "SKU1", "categoria_id": self.cat, "preco_custo": "11", "preco_venda": "25",
                                                              "estoque_minimo": "3", "unidade": "unidade", "estoque_atual": "9999", "quantidade_inicial": "9999"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.estoque(), 10)
        self.assertEqual(self.q("SELECT nome FROM produtos")[0]["nome"], "Mouse Novo")

    def test_desativar_preserva_historico_e_bloqueia_movimentacao(self):
        self.novo_produto(inicial=10)
        pid = self.produto_id()
        self.client.post(f"/produtos/{pid}/status")
        self.assertEqual(len(self.q("SELECT 1 FROM produtos")), 1)
        self.assertEqual(len(self.q("SELECT 1 FROM movimentacoes")), 1)
        r = self.client.post("/movimentacoes/entrada/nova", data={"produto_id": pid, "quantidade": 1, "motivo": "compra"})
        self.assertIn("inativo", r.get_data(as_text=True))
        self.assertTrue(self.q("SELECT 1 FROM logs WHERE acao='Desativação'"))

    def test_listagem_filtros_e_paginacao(self):
        for i in range(45):
            self.novo_produto(sku=f"P{i:03d}", nome=f"Item {i}", inicial=0 if i % 3 == 0 else 50, minimo=5)
        html = self.client.get("/produtos").get_data(as_text=True)
        self.assertIn("Mostrando 1–20 de 45", html)
        self.assertIn("Mostrando 41–45 de 45", self.client.get("/produtos?page=3").get_data(as_text=True))
        self.assertIn("de 15", self.client.get("/produtos?status=esgotado").get_data(as_text=True))
        self.assertIn("Item 7", self.client.get("/produtos?q=Item 7").get_data(as_text=True))
        self.assertEqual(self.client.get("/produtos?categoria_id=abc&page=zzz").status_code, 200)  # entrada maliciosa não derruba

    def test_busca_sem_resultado(self):
        self.assertIn("Nenhum produto encontrado", self.client.get("/produtos?q=xyzinexistente").get_data(as_text=True))

    def test_sql_injection_nao_funciona(self):
        self.novo_produto(inicial=1)
        r = self.client.get("/produtos?q=' OR 1=1; DROP TABLE produtos;--")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self.q("SELECT 1 FROM produtos")), 1)
        self.assertEqual(self.client.get("/busca?q=' OR '1'='1").status_code, 200)

    def test_upload_rejeita_arquivo_nao_imagem(self):
        import io
        r = self.client.post("/produtos/novo", data={"nome": "P", "sku": "IMG", "categoria_id": self.cat, "preco_custo": "1", "estoque_minimo": "1", "unidade": "unidade",
                                                     "imagem": (io.BytesIO(b"<?php evil ?>"), "x.php")}, content_type="multipart/form-data")
        self.assertIn("Imagem inválida", r.get_data(as_text=True))
        r = self.client.post("/produtos/novo", data={"nome": "P", "sku": "IMG", "categoria_id": self.cat, "preco_custo": "1", "estoque_minimo": "1", "unidade": "unidade",
                                                     "imagem": (io.BytesIO(b"not really png"), "x.png")}, content_type="multipart/form-data")
        self.assertIn("não é uma imagem válida", r.get_data(as_text=True))
