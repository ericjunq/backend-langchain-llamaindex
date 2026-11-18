# CHECKLIST — backend-langchain-llamaindex

## 🎯 Visão do produto (definida pelo usuário em 2026-11-17)

Sistema para empresas: um usuário **cria uma empresa** (vira dono) ou **entra numa empresa** como funcionário, por convite. A partir daí:

1. **Gestão**: estoque, produtos, clientes, vendas e funcionários (cargos `dono`, `admin` e `funcionario`).
2. **Relatórios** de vendas e produtos, com exportação (Excel).
3. **IA de previsão**: projeções de vendas e produtos (quantidades, preços, demanda, reposição de estoque).
4. **Agentes via chatbot**: o usuário escreve em linguagem natural e o agente executa ações no sistema (LangChain/LlamaIndex).
5. **Frontend em Angular**, bem acabado (consome esta API; o CORS já está liberado para `localhost:4200`).

Stack: FastAPI, SQLAlchemy 2 (sem Alembic), Pydantic v2, PostgreSQL (psycopg 3), pandas.

## 📍 Onde paramos

- **2026-11-17**: todas as correções da avaliação aplicadas (bloqueantes, segurança, desempenho e LGPD). Teste de fumaça ponta a ponta com 37 cenários passando (SQLite em memória, fora do repositório).
- **2026-11-18**: ambiente configurado. `.env` criado (Postgres local, `SECRET_KEY` aleatória). Banco `gestao` criado do zero (não existia; nenhum dado apagado), com as 8 tabelas e os índices. Teste de fumaça com 37 cenários passando **no Postgres** (banco temporário `gestao_teste`, apagado depois). API sobe sem erros (34 rotas). Subir com: `uvicorn main:app --reload` e abrir a documentação em `/docs`.
- **2026-11-18**: **testes automatizados** em `tests/` (pytest): 60 testes, ~22 s, todos passando. Rodar com `python -m pytest`. O banco `gestao_teste` é criado e apagado sozinho; o `gestao` nunca é tocado. Os testes pegam regressões: reintroduzir o bug do "convite sem cargo" derruba 5 deles.
- **Próximos passos sugeridos:**
  1. Relatório de **produtos** (giro, margem, abaixo do estoque mínimo, sem venda no período).
  3. Envio de email (transparência LGPD: troca de senha/email) e rotas de direitos do titular.
  4. IA de previsão → agentes/chatbot → frontend Angular.

## ✅ Feito em 2026-11-17

- **Bloqueantes:** `sub` do JWT como string; relacionamentos dos models; `codigo_produto` (String "PROD-XXXXXXXX"); `criar_venda` (empresa/usuário, Decimal); convite (token, timezone); logout invertido; filtro de semestre/ano; schemas de resposta; filtros `Optional` obrigatórios; `buscar_produto`.
- **Filtro de data unificado** (`utils/data_filter.py`): `?periodo=mes|semestre|ano` **ou** `?data_inicial=&data_final=` (query params). Os dois ao mesmo tempo → 400.
- **Paginação** (`utils/paginacao.py`): `?limite=50&offset=0` (máx. 200) em todas as listagens, sem `COUNT` extra.
- **Permissões** centralizadas em `security/permissoes.py`.
- **Vendas:** quantidades > 0; cliente precisa ser da mesma empresa; itens repetidos agrupados; produtos lidos numa consulta só com `FOR UPDATE` ordenado por id (sem venda acima do estoque e sem deadlock); valores calculados no servidor (o cliente não manda mais `valor_total`/`valor_final`); funcionário só lista as próprias vendas.
- **Convite** agora define `cargo=funcionario`. Antes ficava `None`, e o funcionário passava nas checagens como se fosse admin.
- **Rotas em `def`** (não `async def`), porque o SQLAlchemy é síncrono e `async` travava o servidor.
- **Índices:** `(empresa_id, created_at)` em vendas, clientes e produtos; FKs de itens, clientes, vendas, tokens e convites; `expires_at`.
- **Preços** em `Numeric(10,2)`.
- **Refresh token:** SHA-256 em vez de Argon2; enviado no **corpo** (`{"refresh_token": ...}`), não no header. Rota nova `/usuario/me`.
- **Usuário:** email, CPF e telefone únicos no sistema todo; email em minúsculas; CPF, CNPJ e telefone salvos só com dígitos (aceita máscara na entrada); senha mínima de 8; trocar email/senha exige `senha_atual`; trocar a senha encerra as outras sessões.
- **Relatório:** rotas `GET /relatorios/vendas` e `GET /relatorios/vendas/exportar` (só dono). Agora são 4 consultas em vez de ~13. O faturamento respeita o filtro e usa `valor_final`; o ticket médio exclui canceladas. O Excel é gerado em memória.
- **Exclusões:** cliente com vendas é **anonimizado** (LGPD); produto com vendas é **desativado** (`ativo=False`).
- **Login:** sempre 401 e tempo constante (não revela se o email existe).
- **Retenção:** ao iniciar, apaga refresh tokens e convites vencidos.
- **Infra:** `requirements.txt` e `.env.example`; `FormaPagamento.dinheiro` adicionado; `editar_produto` virou PATCH.

## 🔜 Pendências conhecidas

- [x] Testes automatizados no repositório (60 testes)
- [ ] Teste de concorrência real (duas vendas simultâneas do último item). Hoje o `FOR UPDATE` só é coberto indiretamente
- [ ] Limpeza de dados vencidos só roda ao iniciar → agendar (ex.: tarefa diária)
- [ ] Email de aviso (troca de senha/email, novo login), hoje como TODO em `usuario_service.editar_usuario`
- [ ] Direitos do titular: exportar "meus dados", anonimizar a própria conta
- [ ] Rate limit no login (força bruta)
- [ ] Relatório de produtos
- [ ] Empresa: desativar/excluir; transferência de dono
- [ ] Busca de produto por nome usa `LIKE '%x%'` (não usa índice). Se o volume crescer: `pg_trgm`
- [ ] Rever a decisão "sem Alembic" antes de ir para produção com dados reais

## 🧵 Trilha de ideias

- **2026-11-17**: avaliação completa do projeto. Contexto reconstruído e problemas classificados (bloqueante → segurança → desempenho → LGPD → infra). Decisão: estabilizar o núcleo antes de relatórios e IA, porque a IA vai consultar esses mesmos dados.
- **2026-11-17**: o CLAUDE.md tinha vindo de um projeto PHP/Laravel. Foi adaptado para Python (seção "Stack"; "aluno" virou usuário, dono e cliente).
- **2026-11-17**: decisão do usuário: **sem Alembic**. A estrutura fica só nos models (`create_all`). Alterar model = `drop_all` + `create_all` (apaga os dados → só com confirmação). Rever antes de produção.
- **2026-11-17**: visão do produto registrada (gestão + relatórios + IA de previsão + agentes via chatbot + Angular).
- **2026-11-17**: correções aplicadas. Decisões e porquês:
  - Exclusão de cliente com vendas → **anonimizar** em vez de apagar: o histórico financeiro precisa ficar, os dados pessoais não (LGPD).
  - Produto com vendas → **desativar**: preserva o histórico e os relatórios (base para a IA de previsão).
  - Paginação **sem total** (sem `COUNT`): um `COUNT` a mais por listagem custa caro em tabela grande. O frontend pode usar "carregar mais".
  - Relatório: agregação única por entidade, com os rankings feitos em pandas. Troca: traz uma linha por produto/funcionário/cliente que vendeu (volume pequeno) em vez de 10 consultas com `LIMIT 5`.
  - Funcionário só vê as próprias vendas (mínima exposição), seguindo a regra já usada em `listar_vendas_funcionario`.
  - Refresh token no corpo da requisição: facilita o interceptor do Angular e separa claramente do access token.
- **2026-11-18**: regra combinada: **apresentar o plano de implementação antes de cada alteração** (registrada no CLAUDE.md). Testes rodam num banco temporário separado para nunca sujar o `gestao`.
- **2026-11-18**: testes automatizados. Decisões:
  - **Postgres real**, não SQLite: `FOR UPDATE`, `FILTER`, enums e timezone só se comportam de verdade no Postgres.
  - Banco `<nome>_teste` derivado do `.env` (ou `TEST_DATABASE_URL`), com trava: o conftest se recusa a rodar se o nome não terminar em `_teste`.
  - `create_all` uma vez por execução e `TRUNCATE ... RESTART IDENTITY` entre testes (rápido).
  - `tests/fabrica.py` gera CPF, CNPJ e telefone válidos e fictícios (LGPD: nenhum dado real nos testes).
  - Organização por área: auth, empresa, produtos, clientes, vendas, **isolamento entre empresas**, relatórios e retenção.
