from tests.base import BaseTest


class TestPermissoes(BaseTest):
    def test_visualizador_somente_leitura(self):
        self.login("admin")
        self.novo_produto(inicial=10)
        pid = self.produto_id()
        v = self.app.test_client()
        self.login("visualizador", v)
        for url in ("/dashboard", "/produtos", f"/produtos/{pid}", "/categorias", "/fornecedores", "/clientes", "/movimentacoes", "/relatorios/estoque"):
            self.assertEqual(v.get(url).status_code, 200, url)
        for url in ("/produtos/novo", "/movimentacoes/entrada/nova", "/movimentacoes/saida/nova", "/usuarios", "/auditoria", "/configuracoes", "/categorias/nova"):
            self.assertEqual(v.get(url).status_code, 403, url)
        r = v.post("/movimentacoes/entrada/nova", data={"produto_id": pid, "quantidade": 5, "motivo": "compra"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.estoque(), 10)
        self.assertEqual(v.post(f"/produtos/{pid}/status").status_code, 403)

    def test_funcionario_movimenta_mas_nao_administra(self):
        self.login("admin")
        self.novo_produto(inicial=10)
        pid = self.produto_id()
        f = self.app.test_client()
        self.login("funcionario", f)
        r = f.post("/movimentacoes/saida/nova", data={"produto_id": pid, "quantidade": 3, "motivo": "venda"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.estoque(), 7)
        for url in ("/usuarios", "/usuarios/novo", "/auditoria", "/configuracoes", "/movimentacoes/ajuste/nova", "/produtos/novo"):
            self.assertEqual(f.get(url).status_code, 403, url)
        self.assertEqual(f.post(f"/usuarios/{self.ids['visualizador']}/editar", data={}).status_code, 403)

    def test_funcionario_nao_faz_ajuste(self):
        self.login("admin")
        self.novo_produto(inicial=10)
        f = self.app.test_client()
        self.login("funcionario", f)
        r = f.post("/movimentacoes/ajuste/nova", data={"produto_id": self.produto_id(), "novo_estoque": 99, "motivo": "outros", "observacao": "x"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.estoque(), 10)

    def test_admin_acessa_tudo(self):
        self.login("admin")
        for url in ("/usuarios", "/usuarios/novo", "/auditoria", "/configuracoes", "/movimentacoes/ajuste/nova", "/produtos/novo", "/relatorios"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_pagina_403_amigavel(self):
        v = self.app.test_client()
        self.login("visualizador", v)
        r = v.get("/usuarios")
        self.assertIn("Acesso negado", r.get_data(as_text=True))
        self.assertIn("não possui permissão", r.get_data(as_text=True))

    def test_nao_rebaixa_unico_admin(self):
        self.login("admin")
        r = self.client.post(f"/usuarios/{self.ids['admin']}/editar", data={"nome": "Usuario Admin", "usuario": "admin", "email": "admin@t.com", "perfil": "visualizador"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("único administrador", r.get_data(as_text=True))

    def test_alterar_permissao_e_auditado(self):
        self.login("admin")
        r = self.client.post(f"/usuarios/{self.ids['visualizador']}/editar", data={"nome": "Usuario Visualizador", "usuario": "visualizador", "email": "visualizador@t.com", "perfil": "funcionario"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(self.q("SELECT 1 FROM logs WHERE acao='Alteração de permissão'"))

    def test_pagina_404(self):
        self.login("admin")
        r = self.client.get("/produtos/9999")
        self.assertEqual(r.status_code, 404)
        self.assertIn("não encontrada", r.get_data(as_text=True))
