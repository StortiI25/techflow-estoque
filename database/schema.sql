-- Schema do TechFlow Estoque (SQL padrão; compatível com SQLite e portável para PostgreSQL)
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    telefone TEXT,
    cargo TEXT,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL DEFAULT 'visualizador' CHECK (perfil IN ('admin','funcionario','visualizador')),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    ultimo_login TEXT
);

CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    cnpj TEXT UNIQUE,
    email TEXT,
    telefone TEXT,
    endereco TEXT,
    cidade TEXT,
    estado TEXT,
    observacoes TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    documento TEXT UNIQUE,
    email TEXT,
    telefone TEXT,
    endereco TEXT,
    cidade TEXT,
    estado TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    codigo_barras TEXT UNIQUE,
    nome TEXT NOT NULL,
    descricao TEXT,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    preco_custo REAL NOT NULL DEFAULT 0 CHECK (preco_custo >= 0),
    preco_venda REAL NOT NULL DEFAULT 0 CHECK (preco_venda >= 0),
    estoque_atual INTEGER NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
    estoque_minimo INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    estoque_maximo INTEGER CHECK (estoque_maximo IS NULL OR estoque_maximo >= 0),
    unidade TEXT NOT NULL DEFAULT 'unidade',
    imagem TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    cliente_id INTEGER REFERENCES clientes(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada','saida','ajuste')),
    motivo TEXT NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    estoque_anterior INTEGER NOT NULL CHECK (estoque_anterior >= 0),
    estoque_posterior INTEGER NOT NULL CHECK (estoque_posterior >= 0),
    valor_unitario REAL NOT NULL DEFAULT 0,
    valor_total REAL NOT NULL DEFAULT 0,
    observacao TEXT,
    data_hora TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    acao TEXT NOT NULL,
    entidade TEXT,
    entidade_id INTEGER,
    descricao TEXT,
    ip TEXT,
    data_hora TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS notificacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),   -- NULL = notificação global (todos os usuários)
    produto_id INTEGER REFERENCES produtos(id),
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    mensagem TEXT,
    lida INTEGER NOT NULL DEFAULT 0,
    criada_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id);
CREATE INDEX IF NOT EXISTS idx_produtos_fornecedor ON produtos(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacoes(produto_id, data_hora);
CREATE INDEX IF NOT EXISTS idx_mov_data ON movimentacoes(data_hora);
CREATE INDEX IF NOT EXISTS idx_mov_cliente ON movimentacoes(cliente_id);
CREATE INDEX IF NOT EXISTS idx_mov_fornecedor ON movimentacoes(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_logs_data ON logs(data_hora);
CREATE INDEX IF NOT EXISTS idx_notif_lida ON notificacoes(lida, criada_em);

-- Histórico e auditoria são imutáveis: correções são feitas com movimentações de ajuste.
CREATE TRIGGER IF NOT EXISTS mov_sem_update BEFORE UPDATE ON movimentacoes
BEGIN SELECT RAISE(ABORT, 'Movimentações não podem ser alteradas. Crie um ajuste.'); END;
CREATE TRIGGER IF NOT EXISTS mov_sem_delete BEFORE DELETE ON movimentacoes
BEGIN SELECT RAISE(ABORT, 'Movimentações não podem ser apagadas. Crie um ajuste.'); END;
CREATE TRIGGER IF NOT EXISTS logs_sem_update BEFORE UPDATE ON logs
BEGIN SELECT RAISE(ABORT, 'Logs de auditoria não podem ser alterados.'); END;
CREATE TRIGGER IF NOT EXISTS logs_sem_delete BEFORE DELETE ON logs
BEGIN SELECT RAISE(ABORT, 'Logs de auditoria não podem ser apagados.'); END;

INSERT OR IGNORE INTO configuracoes(chave, valor) VALUES
    ('empresa_nome', 'TechFlow Estoque'),
    ('dias_sem_movimentacao', '30'),
    ('permitir_cadastro_publico', '0');
