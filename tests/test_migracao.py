import os
import sqlite3

from werkzeug.security import generate_password_hash

from database.migrar_legado import migrar
from tests.base import BaseTest


class TestMigracaoLegado(BaseTest):
    def test_migra_dados_do_schema_antigo(self):
        caminho = os.path.join(self.tmp.name, "legado.db")
        c = sqlite3.connect(caminho)
        c.executescript("""
        CREATE TABLE usuarios(id INTEGER PRIMARY KEY, nome TEXT, usuario TEXT, email TEXT, telefone TEXT, cargo TEXT, senha TEXT, perfil TEXT, ativo INTEGER, criado_em TEXT);
        CREATE TABLE clientes(id INTEGER PRIMARY KEY, nome TEXT, email TEXT, telefone TEXT, endereco TEXT, criado_em TEXT);
        CREATE TABLE produtos(id INTEGER PRIMARY KEY, codigo_barras TEXT, nome TEXT, categoria TEXT, preco_custo REAL, preco_venda REAL, estoque INTEGER, estoque_minimo INTEGER, criado_em TEXT);
        """)
        h = generate_password_hash("Antiga@123")
        c.execute("INSERT INTO usuarios VALUES(1,'Dono Antigo',NULL,'dono@old.com','1199','Chefe',?,'admin',1,'x')", (h,))
        c.execute("INSERT INTO usuarios VALUES(2,'Func Antigo','func','admin@t.com','1199','',?,'funcionario',1,'x')", (h,))  # e-mail já existe -> ignora
        c.execute("INSERT INTO clientes VALUES(1,'Cliente Velho','c@old.com','1133','Rua A','x')")
        c.execute("INSERT INTO produtos VALUES(1,'789','Notebook','Informática',3000,3899.9,12,3,'x')")
        c.execute("INSERT INTO produtos VALUES(2,'789','Mouse',NULL,10,20,0,2,'x')")  # barras repetido -> vira NULL; sem categoria -> Outros
        c.commit(); c.close()
        with self.app.app_context():
            r = migrar(caminho)
        self.assertEqual((r["usuarios"], r["clientes"], r["produtos"]), (1, 1, 2))
        self.assertEqual(len(r["ignorados"]), 1)
        self.assertEqual(self.q("SELECT estoque_atual FROM produtos WHERE sku='LEG-0001'")[0]["estoque_atual"], 12)
        self.assertEqual(self.q("SELECT tipo, quantidade, estoque_posterior FROM movimentacoes")[0], {"tipo": "entrada", "quantidade": 12, "estoque_posterior": 12})
        self.assertTrue(self.q("SELECT 1 FROM categorias WHERE nome='Outros'"))
        # a senha antiga continua válida (hash preservado)
        r = self.app.test_client().post("/login", data={"identificador": "dono@old.com", "senha": "Antiga@123"})
        self.assertEqual(r.status_code, 302)
