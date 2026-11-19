-- V002: permite anonimizar a conta do usuário (LGPD: direito à anonimização).
-- CPF e telefone passam a aceitar NULL: na anonimização eles são apagados, mas o registro do
-- usuário continua existindo (vendas e clientes apontam para ele: histórico financeiro).
-- O UNIQUE continua valendo (o Postgres permite vários NULL numa coluna UNIQUE).

ALTER TABLE usuarios ALTER COLUMN cpf DROP NOT NULL;
ALTER TABLE usuarios ALTER COLUMN telefone DROP NOT NULL;
