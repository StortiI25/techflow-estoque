"""IP do cliente atrás de proxy (Render): bloqueio de login e auditoria não podem usar o IP do proxy."""
import os

from app import create_app
from database.database import query
from models import usuario
from tests.base import BaseTest

PROXY = {"REMOTE_ADDR": "10.0.0.1"}  # todos os clientes chegam com o IP do proxy


class ProxyTest(BaseTest):
    def _erros(self, client, ip_real, vezes):
        for _ in range(vezes):
            client.post("/login", data={"identificador": "x@t.com", "senha": "errada"},
                        environ_base=PROXY, headers={"X-Forwarded-For": ip_real})

    def _login(self, client, ip_real):
        return client.post("/login", data={"identificador": "admin@t.com", "senha": "Admin@123"},
                           environ_base=PROXY, headers={"X-Forwarded-For": ip_real})

    def test_sem_proxy_configurado_o_cabecalho_e_ignorado(self):
        # padrão (PROXY_HOPS=0): X-Forwarded-For não pode ser usado para trocar/forjar o IP
        self._erros(self.client, "200.1.1.1", 5)
        r = self._login(self.client, "200.9.9.9")
        self.assertEqual(r.status_code, 401)
        self.assertIn("Muitas tentativas", r.get_data(as_text=True))

    def test_com_proxy_bloqueio_vale_so_para_o_ip_real(self):
        app = create_app({"TESTING": True, "DATABASE": os.path.join(self.tmp.name, "proxy.db"), "UPLOAD_FOLDER": self.tmp.name,
                          "CSRF_ENABLED": False, "SECRET_KEY": "teste", "PROXY_HOPS": 1})
        with app.app_context():
            usuario.criar({"nome": "Usuario Admin", "usuario": "admin", "email": "admin@t.com", "telefone": "",
                           "cargo": "", "senha": "Admin@123", "perfil": "admin"})
        c = app.test_client()
        self._erros(c, "200.1.1.1", 5)
        self.assertEqual(self._login(c, "200.1.1.1").status_code, 401)  # mesmo IP real: continua bloqueado
        self.assertEqual(self._login(c, "200.9.9.9").status_code, 302)  # outro IP atrás do mesmo proxy: entra
        with app.app_context():
            ips = {r["ip"] for r in query("SELECT ip FROM logs WHERE acao='Login'")}
        self.assertEqual(ips, {"200.9.9.9"})  # auditoria grava o IP real, não o do proxy
