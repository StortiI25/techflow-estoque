import os
import tempfile
import unittest

from app import create_app
from database.database import execute
from models import categoria, cliente, fornecedor, usuario
from routes import auth


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": os.path.join(self.tmp.name, "t.db"), "UPLOAD_FOLDER": self.tmp.name,
                               "CSRF_ENABLED": False, "SECRET_KEY": "teste"})
        self.client = self.app.test_client()
        auth._falhas.clear()
        with self.app.app_context():
            self.ids = {}
            for perfil, senha in (("admin", "Admin@123"), ("funcionario", "Func@123"), ("visualizador", "Visu@123")):
                self.ids[perfil] = usuario.criar({"nome": f"Usuario {perfil.title()}", "usuario": perfil, "email": f"{perfil}@t.com", "telefone": "", "cargo": "",
                                                  "senha": senha, "perfil": perfil})
            self.cat = categoria.criar({"nome": "Informática", "descricao": ""})
            self.forn = fornecedor.criar({"razao_social": "Forn Teste", "nome_fantasia": "", "cnpj": "", "email": "", "telefone": "", "endereco": "", "cidade": "", "estado": "", "observacoes": ""})
            self.cli = cliente.criar({"nome": "Cliente Teste", "documento": "", "email": "", "telefone": "", "endereco": "", "cidade": "", "estado": ""})

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, perfil="admin", client=None):
        senha = {"admin": "Admin@123", "funcionario": "Func@123", "visualizador": "Visu@123"}[perfil]
        c = client or self.client
        r = c.post("/login", data={"identificador": f"{perfil}@t.com", "senha": senha})
        self.assertEqual(r.status_code, 302, "login deveria redirecionar")
        return c

    def novo_produto(self, sku="SKU1", nome="Mouse", inicial=0, minimo=5, **extra):
        dados = {"nome": nome, "sku": sku, "categoria_id": self.cat, "preco_custo": "10.00", "preco_venda": "20.00", "estoque_minimo": str(minimo),
                 "unidade": "unidade", "quantidade_inicial": str(inicial), **extra}
        r = self.client.post("/produtos/novo", data=dados)
        return r

    def produto_id(self, sku="SKU1"):
        with self.app.app_context():
            return execute("SELECT id FROM produtos WHERE sku=?", (sku,)).fetchone()["id"]

    def estoque(self, sku="SKU1"):
        with self.app.app_context():
            return execute("SELECT estoque_atual FROM produtos WHERE sku=?", (sku,)).fetchone()["estoque_atual"]

    def q(self, sql, params=()):
        with self.app.app_context():
            return [dict(r) for r in execute(sql, params).fetchall()]
