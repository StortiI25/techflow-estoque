from tests.base import BaseTest


class TestAuth(BaseTest):
    def test_rotas_exigem_login(self):
        for url in ("/dashboard", "/produtos", "/movimentacoes", "/relatorios", "/usuarios", "/auditoria"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"])

    def test_login_valido_por_email_e_por_usuario(self):
        self.login("admin")
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        c2 = self.app.test_client()
        r = c2.post("/login", data={"identificador": "funcionario", "senha": "Func@123"})
        self.assertEqual(r.status_code, 302)

    def test_login_invalido(self):
        r = self.client.post("/login", data={"identificador": "admin@t.com", "senha": "errada"})
        self.assertEqual(r.status_code, 401)
        self.assertIn("inválidos", r.get_data(as_text=True))
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_senha_nunca_em_texto_puro(self):
        for u in self.q("SELECT senha_hash FROM usuarios"):
            self.assertNotIn("Admin@123", u["senha_hash"])
            self.assertTrue(u["senha_hash"].startswith(("scrypt:", "pbkdf2:")))

    def test_logout_encerra_sessao(self):
        self.login("admin")
        self.assertEqual(self.client.post("/logout").status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_usuario_bloqueado_nao_entra_e_perde_sessao(self):
        c = self.login("funcionario")
        self.assertEqual(c.get("/dashboard").status_code, 200)
        from database.database import execute
        with self.app.app_context():
            execute("UPDATE usuarios SET ativo=0 WHERE usuario='funcionario'")
        self.assertEqual(c.get("/dashboard").status_code, 302)
        r = self.app.test_client().post("/login", data={"identificador": "funcionario", "senha": "Func@123"})
        self.assertEqual(r.status_code, 401)
        self.assertIn("bloqueada", r.get_data(as_text=True))

    def test_bloqueio_por_excesso_de_tentativas(self):
        for _ in range(5):
            self.client.post("/login", data={"identificador": "admin", "senha": "x"})
        r = self.client.post("/login", data={"identificador": "admin", "senha": "Admin@123"})
        self.assertEqual(r.status_code, 401)
        self.assertIn("Muitas tentativas", r.get_data(as_text=True))

    def test_redirect_next_so_aceita_caminho_interno(self):
        r = self.client.post("/login?next=//evil.com", data={"identificador": "admin", "senha": "Admin@123"})
        self.assertNotIn("evil.com", r.headers["Location"])

    def test_login_e_logout_auditados(self):
        self.login("admin")
        self.client.post("/logout")
        acoes = [l["acao"] for l in self.q("SELECT acao FROM logs")]
        self.assertIn("Login", acoes)
        self.assertIn("Logout", acoes)

    def test_csrf_bloqueia_post_sem_token(self):
        self.app.config["CSRF_ENABLED"] = True
        r = self.client.post("/login", data={"identificador": "admin", "senha": "Admin@123"})
        self.assertEqual(r.status_code, 400)

    def test_cadastro_publico_desativado_por_padrao(self):
        self.assertEqual(self.client.get("/registrar").status_code, 404)
