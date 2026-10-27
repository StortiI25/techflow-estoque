# TechFlow Estoque

Sistema web de **controle de estoque** para uma empresa de tecnologia: cadastro de produtos, entradas e saídas,
alertas de estoque baixo, relatórios e trilha de auditoria. Feito em **Python + Flask + SQLite**.

## Funcionalidades

- **Produtos, categorias, fornecedores e clientes**: cadastro completo, validação de CPF/CNPJ, upload de imagem do produto e
  desativação em vez de exclusão (o histórico é preservado).
- **Movimentações**: entrada, saída e ajuste de inventário. O saldo do produto só muda por movimentação, e cada uma guarda o
  estoque antes e depois, o motivo e quem fez.
- **Dashboard**: indicadores, gráficos por categoria e por período, produtos críticos e parados.
- **Alertas**: notificações automáticas de estoque abaixo do mínimo, esgotado ou acima do máximo.
- **Relatórios**: estoque, movimentações e estoque baixo, com filtros e exportação em CSV.
- **Busca global** e **auditoria** de logins, edições e exportações.
- **Perfis de acesso**: administrador, funcionário e visualizador.

| Perfil | Ver | Movimentar estoque | Relatórios | Cadastros, usuários, logs e configurações |
|---|:-:|:-:|:-:|:-:|
| Administrador | ✅ | ✅ | ✅ | ✅ |
| Funcionário | ✅ | ✅ | ✅ | ❌ |
| Visualizador | ✅ | ❌ | ✅ | ❌ |

## Como rodar

Testado com Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m database.seed          # cria o banco com dados de demonstração
python app.py                    # abre em http://localhost:5000
```

Usuários de demonstração (criados pelo seed; **não use essas senhas em produção**):

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador | admin@techflow.com | Admin@123 |
| Funcionário | funcionario@techflow.com | Func@123 |
| Visualizador | visualizador@techflow.com | Visu@123 |

Para recriar o banco do zero: `python -m database.seed --reset`.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem autenticação, permissões por perfil, regras de estoque (inclusive saída maior que o saldo), movimentações,
produtos, migração de dados legados e o comportamento do login atrás de proxy.

## Arquitetura

```
app.py            fábrica da aplicação (blueprints, hooks, tratamento de erros, CLI)
config.py         configurações (valores sensíveis vêm de variáveis de ambiente)
routes/           camada web: recebe a requisição, valida permissão, chama services e renderiza
services/         regras de negócio (estoque, notificações, relatórios, auditoria)
models/           consultas SQL por entidade
database/         conexão, schema.sql, seed e migração
utils/            segurança (RBAC, CSRF), validadores e formatadores
templates/ static/   interface (Jinja2, Bootstrap, JavaScript)
tests/            testes automatizados
```

Decisões de projeto que valem destaque:

- **Um único ponto altera o saldo**: `services/estoque_service.py`. Rotas e models nunca atualizam `estoque_atual` direto.
- **Transações atômicas** (`BEGIN IMMEDIATE`): ler o saldo, validar e gravar acontecem juntos, então duas saídas simultâneas
  não deixam o estoque negativo.
- **Histórico imutável**: *triggers* no banco proíbem `UPDATE` e `DELETE` em movimentações e logs. Correções são feitas
  com um ajuste de inventário, que fica registrado.
- **Segurança**: senhas com hash, proteção CSRF, cookies `HttpOnly`/`SameSite`, bloqueio após 5 logins errados em 10 minutos,
  permissões checadas no backend, upload validado por extensão **e** assinatura do arquivo, e CSV protegido contra injeção de fórmulas.

## Variáveis de ambiente

| Variável | Para que serve | Padrão |
|---|---|---|
| `SECRET_KEY` | Chave das sessões. **Defina em produção.** | gerada a cada start |
| `DATABASE_PATH` | Caminho do arquivo SQLite | `database/techflow.db` |
| `SESSION_COOKIE_SECURE` | `1` para enviar o cookie só por HTTPS | desligado |
| `PROXY_HOPS` | Nº de proxies na frente do app (Render = `1`). Faz o login e a auditoria usarem o IP real do usuário | `0` |
| `PORT`, `FLASK_DEBUG` | Porta e modo debug do `python app.py` | `5000`, desligado |

## Deploy no Render

O `render.yaml` já está pronto: crie um *Blueprint* apontando para o repositório e adicione um **Disk persistente** montado
em `/var/data` (o SQLite fica lá). Depois do primeiro deploy, rode `python -m database.seed` no *Shell* do serviço se quiser
os dados de demonstração.

> Depois de publicar, confira na tela **Auditoria** se o IP registrado nos logins é o seu IP real. Se aparecer o IP
> do próprio Render, ajuste `PROXY_HOPS`.

## Limitações conhecidas e próximos passos

- **Valores monetários** estão em `REAL` (ponto flutuante). Para um sistema financeiro de verdade, o ideal é guardar em centavos (inteiro).
- O **bloqueio de login** fica na memória de cada processo. Com vários *workers* ou instâncias, o ideal é usar Redis ou o banco.
- **Recuperação de senha** é manual (feita por um administrador); falta o envio de e-mail com link de redefinição.
- **SQLite** atende bem uma instância; para várias, migrar para PostgreSQL (o acesso ao banco está concentrado em `database/database.py`).
- Relatórios só exportam CSV; PDF pode ser adicionado em `services/relatorio_service.py`.

## Licença

MIT. Veja [LICENSE](LICENSE).
