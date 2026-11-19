-- V003: trilha de auditoria.
-- Registra escritas (cadastros, edições, exclusões, estoque, vendas, cargos, convites, conta),
-- exportações de dados e eventos de acesso (login, falha de login, reuso de token).
-- Retenção (rotina de limpeza): categoria 'acesso' = 1 ano; 'operacao' e 'venda' = 5 anos.
-- LGPD: campos pessoais alterados ficam só como "alterado"; IP apenas em eventos de acesso.

CREATE TABLE auditoria (
	id BIGSERIAL NOT NULL, 
	empresa_id INTEGER, 
	usuario_id INTEGER, 
	categoria VARCHAR(10) NOT NULL, 
	acao VARCHAR(40) NOT NULL, 
	entidade VARCHAR(30), 
	entidade_id VARCHAR(36), 
	origem VARCHAR(10) DEFAULT 'api' NOT NULL, 
	detalhes JSON, 
	ip VARCHAR(45), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(empresa_id) REFERENCES empresas (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

CREATE INDEX ix_auditoria_entidade ON auditoria (entidade, entidade_id);

CREATE INDEX ix_auditoria_categoria_created ON auditoria (categoria, created_at);

CREATE INDEX ix_auditoria_empresa_created ON auditoria (empresa_id, created_at);

CREATE INDEX ix_auditoria_usuario_id ON auditoria (usuario_id);
