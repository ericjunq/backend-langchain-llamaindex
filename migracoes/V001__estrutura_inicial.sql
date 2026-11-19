-- V001: estrutura inicial (retrato dos models em 2026-11-18).
-- Gerado uma única vez a partir dos models do SQLAlchemy; daqui em diante, cada mudança de
-- estrutura ou de dados é um NOVO arquivo V00N__descricao.sql (nunca editar um já aplicado).

CREATE TYPE cargosenum AS ENUM ('dono', 'admin', 'funcionario');

CREATE TYPE formapagamento AS ENUM ('pix', 'cartao_credito', 'cartao_debito', 'boleto', 'dinheiro');

CREATE TYPE statusvenda AS ENUM ('concluida', 'cancelada');

CREATE TABLE empresas (
	id SERIAL NOT NULL, 
	nome VARCHAR(40) NOT NULL, 
	cnpj VARCHAR(14) NOT NULL, 
	email VARCHAR(60) NOT NULL, 
	telefone VARCHAR(11) NOT NULL, 
	status BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (cnpj), 
	UNIQUE (email), 
	UNIQUE (telefone)
);

CREATE TABLE usuarios (
	id SERIAL NOT NULL, 
	nome VARCHAR(30) NOT NULL, 
	sobrenome VARCHAR(50) NOT NULL, 
	email VARCHAR(60) NOT NULL, 
	senha_hash VARCHAR(255) NOT NULL, 
	cpf VARCHAR(11) NOT NULL, 
	telefone VARCHAR(11) NOT NULL, 
	cargo cargosenum, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	status BOOLEAN NOT NULL, 
	empresa_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	UNIQUE (cpf), 
	UNIQUE (telefone), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id)
);

CREATE INDEX ix_usuarios_empresa_id ON usuarios (empresa_id);

CREATE TABLE produtos (
	id SERIAL NOT NULL, 
	nome VARCHAR(30) NOT NULL, 
	nome_normalizado VARCHAR(30) NOT NULL, 
	codigo_produto VARCHAR(13) NOT NULL, 
	descricao VARCHAR NOT NULL, 
	quantidade INTEGER NOT NULL, 
	preco_compra NUMERIC(10, 2) NOT NULL, 
	preco_venda NUMERIC(10, 2) NOT NULL, 
	estoque_min INTEGER NOT NULL, 
	ativo BOOLEAN NOT NULL, 
	empresa_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_produto_codigo_empresa UNIQUE (empresa_id, codigo_produto), 
	CONSTRAINT uq_produto_nome_empresa UNIQUE (empresa_id, nome_normalizado), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id)
);

CREATE INDEX ix_produtos_empresa_created ON produtos (empresa_id, created_at);

CREATE TABLE clientes (
	id SERIAL NOT NULL, 
	nome VARCHAR(50) NOT NULL, 
	email VARCHAR(60), 
	telefone VARCHAR(11), 
	cpf VARCHAR(11), 
	empresa_id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	status BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_cliente_email_empresa UNIQUE (empresa_id, email), 
	CONSTRAINT uq_cliente_cpf_empresa UNIQUE (empresa_id, cpf), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_clientes_empresa_created ON clientes (empresa_id, created_at);

CREATE INDEX ix_clientes_usuario_id ON clientes (usuario_id);

CREATE TABLE convites_funcionario (
	id SERIAL NOT NULL, 
	token VARCHAR(64) NOT NULL, 
	usuario_id INTEGER, 
	empresa_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	usado BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (token), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id)
);

CREATE INDEX ix_convites_funcionario_expires_at ON convites_funcionario (expires_at);

CREATE INDEX ix_convites_funcionario_empresa_id ON convites_funcionario (empresa_id);

CREATE TABLE refresh_tokens (
	id SERIAL NOT NULL, 
	jti VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (jti), 
	UNIQUE (token_hash), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_refresh_tokens_expires_at ON refresh_tokens (expires_at);

CREATE INDEX ix_refresh_tokens_usuario_id ON refresh_tokens (usuario_id);

CREATE TABLE acoes_pendentes (
	id VARCHAR(36) NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	empresa_id INTEGER NOT NULL, 
	tipo VARCHAR(30) NOT NULL, 
	dados JSON NOT NULL, 
	resumo VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id)
);

CREATE INDEX ix_acoes_pendentes_expires_at ON acoes_pendentes (expires_at);

CREATE INDEX ix_acoes_pendentes_usuario_id ON acoes_pendentes (usuario_id);

CREATE TABLE vendas (
	id SERIAL NOT NULL, 
	descricao VARCHAR NOT NULL, 
	cliente_id INTEGER, 
	usuario_id INTEGER NOT NULL, 
	valor_total NUMERIC(10, 2) NOT NULL, 
	desconto NUMERIC(10, 2) NOT NULL, 
	valor_final NUMERIC(10, 2) NOT NULL, 
	forma_pagamento formapagamento NOT NULL, 
	empresa_id INTEGER NOT NULL, 
	status statusvenda NOT NULL, 
	motivo_cancelamento VARCHAR(60), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(cliente_id) REFERENCES clientes (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id)
);

CREATE INDEX ix_vendas_empresa_created ON vendas (empresa_id, created_at);

CREATE INDEX ix_vendas_usuario_id ON vendas (usuario_id);

CREATE INDEX ix_vendas_cliente_id ON vendas (cliente_id);

CREATE TABLE itens_vendas (
	id SERIAL NOT NULL, 
	venda_id INTEGER NOT NULL, 
	produto_id INTEGER NOT NULL, 
	quantidade INTEGER NOT NULL, 
	preco_unitario NUMERIC(10, 2) NOT NULL, 
	custo_unitario NUMERIC(10, 2) NOT NULL, 
	subtotal NUMERIC(10, 2) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(venda_id) REFERENCES vendas (id), 
	FOREIGN KEY(produto_id) REFERENCES produtos (id)
);

CREATE INDEX ix_itens_vendas_venda_id ON itens_vendas (venda_id);

CREATE INDEX ix_itens_vendas_produto_id ON itens_vendas (produto_id);
