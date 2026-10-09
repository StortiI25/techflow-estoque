import threading

from database.database import execute
from services import estoque_service
from services.estoque_service import EstoqueError
from tests.base import BaseTest


class TestEstoqueService(BaseTest):
    def setUp(self):
        super().setUp()
        self.login("admin")
        self.novo_produto(inicial=32, minimo=5)
        self.pid = self.produto_id()
        self.uid = self.ids["admin"]

    def test_entrada_soma(self):
        with self.app.app_context():
            r = estoque_service.registrar_entrada(self.pid, 50, "compra", self.uid)
        self.assertEqual((r["anterior"], r["posterior"]), (32, 82))
        self.assertEqual(self.estoque(), 82)

    def test_saida_subtrai(self):
        with self.app.app_context():
            r = estoque_service.registrar_saida(self.pid, 10, "venda", self.uid)
        self.assertEqual((r["anterior"], r["posterior"]), (32, 22))
        self.assertEqual(self.estoque(), 22)

    def test_estoque_nunca_negativo_mensagem_exata(self):
        with self.app.app_context():
            with self.assertRaises(EstoqueError) as ctx:
                estoque_service.registrar_saida(self.pid, 33, "venda", self.uid)
        self.assertEqual(str(ctx.exception), "Estoque insuficiente. Disponível: 32 unidades.")
        self.assertEqual(self.estoque(), 32)
        self.assertEqual(len(self.q("SELECT 1 FROM movimentacoes")), 1)  # nada gravado além do estoque inicial

    def test_saida_exata_zera_mas_nao_negativa(self):
        with self.app.app_context():
            estoque_service.registrar_saida(self.pid, 32, "venda", self.uid)
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_saida(self.pid, 1, "venda", self.uid)
        self.assertEqual(self.estoque(), 0)

    def test_quantidades_invalidas(self):
        with self.app.app_context():
            for q in (0, -5, "abc", "", None, 1.5 * 10**7):
                for fn in (estoque_service.registrar_entrada, estoque_service.registrar_saida):
                    with self.assertRaises(EstoqueError, msg=f"{fn.__name__}({q!r})"):
                        fn(self.pid, q, "compra" if fn is estoque_service.registrar_entrada else "venda", self.uid)
        self.assertEqual(self.estoque(), 32)

    def test_motivo_invalido(self):
        with self.app.app_context():
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_saida(self.pid, 1, "compra", self.uid)  # motivo de entrada em saída
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_entrada(self.pid, 1, "venda", self.uid)

    def test_produto_inexistente(self):
        with self.app.app_context():
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_entrada(9999, 1, "compra", self.uid)

    def test_movimentacao_guarda_todos_os_campos(self):
        with self.app.app_context():
            estoque_service.registrar_saida(self.pid, 4, "venda", self.ids["funcionario"], cliente_id=self.cli, observacao="pedido 1")
        m = self.q("SELECT * FROM movimentacoes ORDER BY id DESC LIMIT 1")[0]
        self.assertEqual((m["tipo"], m["motivo"], m["quantidade"], m["estoque_anterior"], m["estoque_posterior"]), ("saida", "venda", 4, 32, 28))
        self.assertEqual((m["usuario_id"], m["cliente_id"], m["observacao"]), (self.ids["funcionario"], self.cli, "pedido 1"))
        self.assertEqual((m["valor_unitario"], m["valor_total"]), (20.0, 80.0))
        self.assertTrue(m["data_hora"])

    def test_auditoria_gerada(self):
        with self.app.app_context():
            estoque_service.registrar_entrada(self.pid, 5, "compra", self.uid)
            estoque_service.registrar_saida(self.pid, 2, "venda", self.uid)
        acoes = [l["acao"] for l in self.q("SELECT acao FROM logs")]
        self.assertIn("Entrada", acoes)
        self.assertIn("Saída", acoes)

    def test_ajuste_exige_justificativa_e_gera_movimentacao(self):
        with self.app.app_context():
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_ajuste(self.pid, 30, "contagem de inventário", self.uid, "")
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_ajuste(self.pid, -1, "contagem de inventário", self.uid, "x")
            with self.assertRaises(EstoqueError):
                estoque_service.registrar_ajuste(self.pid, 32, "contagem de inventário", self.uid, "igual")
            r = estoque_service.registrar_ajuste(self.pid, 30, "contagem de inventário", self.uid, "contagem física")
        self.assertEqual((r["anterior"], r["posterior"]), (32, 30))
        m = self.q("SELECT tipo, quantidade FROM movimentacoes ORDER BY id DESC LIMIT 1")[0]
        self.assertEqual((m["tipo"], m["quantidade"]), ("ajuste", 2))
        self.assertTrue(self.q("SELECT 1 FROM logs WHERE acao='Ajuste'"))

    def test_banco_recusa_estoque_negativo_mesmo_por_sql_direto(self):
        import sqlite3
        with self.app.app_context():
            with self.assertRaises(sqlite3.IntegrityError):
                execute("UPDATE produtos SET estoque_atual=-1 WHERE id=?", (self.pid,))

    def test_movimentacoes_sao_imutaveis(self):
        import sqlite3
        with self.app.app_context():
            with self.assertRaises(sqlite3.IntegrityError):
                execute("DELETE FROM movimentacoes")
            with self.assertRaises(sqlite3.IntegrityError):
                execute("UPDATE movimentacoes SET quantidade=999")
            with self.assertRaises(sqlite3.IntegrityError):
                execute("DELETE FROM logs")
        self.assertEqual(len(self.q("SELECT 1 FROM movimentacoes")), 1)

    def test_saidas_concorrentes_nao_negativam(self):
        """10 threads tentam retirar 10 un. de um estoque de 32: só 3 podem passar."""
        resultados = []

        def tentar():
            with self.app.app_context():
                try:
                    estoque_service.registrar_saida(self.pid, 10, "venda", self.uid)
                    resultados.append("ok")
                except EstoqueError:
                    resultados.append("recusada")
                except Exception as e:  # noqa: BLE001 - lock do SQLite também protege
                    resultados.append("lock")
        ts = [threading.Thread(target=tentar) for _ in range(10)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(self.estoque(), 32 - 10 * resultados.count("ok"))
        self.assertGreaterEqual(self.estoque(), 0)
        self.assertLessEqual(resultados.count("ok"), 3)


class TestEstoqueHTTP(BaseTest):
    def setUp(self):
        super().setUp()
        self.login("admin")
        self.novo_produto(inicial=32, minimo=5)
        self.pid = self.produto_id()

    def test_saida_insuficiente_pela_interface(self):
        r = self.client.post("/movimentacoes/saida/nova", data={"produto_id": self.pid, "quantidade": 40, "motivo": "venda"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Estoque insuficiente. Disponível: 32 unidades.", r.get_data(as_text=True))
        self.assertEqual(self.estoque(), 32)

    def test_fluxo_completo(self):
        self.client.post("/movimentacoes/entrada/nova", data={"produto_id": self.pid, "quantidade": 50, "motivo": "compra", "fornecedor_id": self.forn})
        self.assertEqual(self.estoque(), 82)
        self.client.post("/movimentacoes/saida/nova", data={"produto_id": self.pid, "quantidade": 10, "motivo": "venda", "cliente_id": self.cli})
        self.assertEqual(self.estoque(), 72)
        html = self.client.get(f"/produtos/{self.pid}").get_data(as_text=True)
        self.assertIn("Histórico de movimentações", html)
        self.assertEqual(len(self.q("SELECT 1 FROM movimentacoes")), 3)
        hist = self.client.get("/movimentacoes").get_data(as_text=True)
        self.assertIn("Mostrando 1–3 de 3", hist)

    def test_preview_api(self):
        j = self.client.get(f"/api/produtos/{self.pid}").get_json()
        self.assertEqual((j["estoque"], j["minimo"]), (32, 5))
        self.assertEqual(self.client.get("/api/produtos/9999").status_code, 404)
        ev = self.client.get(f"/api/produtos/{self.pid}/evolucao").get_json()
        self.assertEqual(ev[-1]["estoque"], 32)

    def test_filtros_do_historico(self):
        self.client.post("/movimentacoes/saida/nova", data={"produto_id": self.pid, "quantidade": 2, "motivo": "perda"})
        self.assertIn("Mostrando 1–1 de 1", self.client.get("/movimentacoes?tipo=saida").get_data(as_text=True))
        self.assertIn("Mostrando 1–1 de 1", self.client.get("/movimentacoes?motivo=perda").get_data(as_text=True))
        self.assertIn("Nenhuma movimentação encontrada", self.client.get("/movimentacoes?data_inicio=2000-01-01&data_fim=2000-01-02").get_data(as_text=True))
        self.assertEqual(self.client.get("/movimentacoes?data_inicio=lixo&produto_id=x").status_code, 200)
