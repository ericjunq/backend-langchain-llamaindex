# CHECKLIST — backend-langchain-llamaindex

## 🎯 Visão do produto (definida pelo usuário em 2026-11-17)

Sistema para empresas: um usuário **cria uma empresa** (vira dono) ou **entra numa empresa** como funcionário, por convite. A partir daí:

1. **Gestão**: estoque, produtos, clientes, vendas e funcionários (cargos `dono`, `admin` e `funcionario`).
2. **Relatórios** de vendas e produtos, com exportação (Excel).
3. **IA de previsão**: projeções de vendas e produtos (quantidades, preços, demanda, reposição de estoque).
4. **Agentes via chatbot**: o usuário escreve em linguagem natural e o agente executa ações no sistema (LangChain/LlamaIndex).
5. **Frontend em Angular**, bem acabado (consome esta API; o CORS já está liberado para `localhost:4200`).

Stack: FastAPI, SQLAlchemy 2 (só consultas), **migrações SQL versionadas** (`migracoes/`), Pydantic v2, PostgreSQL (psycopg 3), pandas, Ollama.

## 📍 Onde paramos

- **2026-11-17**: todas as correções da avaliação aplicadas (bloqueantes, segurança, desempenho e LGPD). Teste de fumaça ponta a ponta com 37 cenários passando (SQLite em memória, fora do repositório).
- **2026-11-18**: ambiente configurado. `.env` criado (Postgres local, `SECRET_KEY` aleatória). Banco `gestao` criado do zero (não existia; nenhum dado apagado), com as 8 tabelas e os índices. Teste de fumaça com 37 cenários passando **no Postgres** (banco temporário `gestao_teste`, apagado depois). API sobe sem erros (34 rotas). Subir com: `uvicorn main:app --reload` e abrir a documentação em `/docs`.
- **2026-11-18**: **testes automatizados** em `tests/` (pytest): 60 testes, ~22 s, todos passando. Rodar com `python -m pytest`. O banco `gestao_teste` é criado e apagado sozinho; o `gestao` nunca é tocado. Os testes pegam regressões: reintroduzir o bug do "convite sem cargo" derruba 5 deles.
- **2026-11-18**: rotas refeitas no **padrão REST** (ver "🗺️ Mapa de rotas"). Commits passam a ser feitos a cada alteração (`tipo: descrição`).
- **2026-11-18**: **relatório de produtos** pronto (`/relatorios/produtos` e `/exportar`). `itens_vendas` ganhou `custo_unitario` → banco `gestao` recriado (estava vazio). 72 testes passando.
- **2026-11-18**: **IA de previsão v1** (estatística, sem LLM): demanda por produto e sugestão de reposição. 80 testes passando.
- **2026-11-18**: Ollama 0.40.16 instalado + modelo `qwen3:8b` (5,2 GB, RTX 3050 6 GB). **Chat com 7 ferramentas de leitura** (`POST /chat`). Testado com o modelo real: ~9 s por resposta com o modelo já carregado (~19 s na primeira). 91 testes + 1 de integração (`OLLAMA_TESTE=1 python -m pytest -k integracao -s`).
- **2026-11-18**: **ações com confirmação no chat**: `registrar_venda` e `repor_estoque` só preparam (tabela `acoes_pendentes`, 10 min); o usuário confirma em `POST /chat/acoes/{id}/confirmar`. Ferramentas recebem produto/cliente **pelo nome**. Testado com o modelo real (~8 s por resposta). 102 testes + integração.
- **2026-11-18**: verificação de segurança do Ollama. Instalador oficial (GitHub, hash conferido pelo winget), assinatura **Ollama Inc./DigiCert** válida, Windows Defender sem ameaças (programa e modelo). Versão 0.40.16 sem as CVEs conhecidas de 2026. Escuta só em `127.0.0.1` + **regra no Firewall do Windows bloqueando a entrada na 11434** (acesso local segue funcionando).
- **2026-11-18**: **emails de aviso** (`services/email_service.py`): troca de senha, troca de email (para os dois endereços) e alerta de sessão comprometida. Backends `console` (dev, só loga o destinatário mascarado), `smtp` (em segundo plano, STARTTLS) e `memoria` (testes).
- **2026-11-18**: **exportar meus dados** (`GET /usuarios/me/dados`, sem cache): perfil completo, empresa, sessões ativas e resumo de atividade. Não inclui hashes nem dados de clientes (pertencem a eles).
- **2026-11-18**: **limite de tentativas de login** (`security/limite_tentativas.py`): 5 falhas em 15 min por **IP + email** → 429. Só pelo email, um atacante bloquearia contas alheias de propósito; só pelo IP, testaria muitas contas. Checado antes de consultar o banco (barra a força bruta sem custo).
- **2026-11-18**: **limpeza agendada**: tarefa em segundo plano no lifespan (sem dependência nova), roda numa thread do pool a cada 24 h. Com vários workers cada um roda a sua, o que é inofensivo (DELETE idempotente).
- **Pendente (decisão do usuário)**: (a) adotar migrações em SQL puro versionadas + prefixo `/api/v1` já, ou (b) só antes de produção; escopo e retenção da **auditoria**. A anonimização da conta e a auditoria esperam essa decisão (mudam o banco).
- **2026-11-18**: usuário aprovou as recomendações: **`/api/v1`** (feito), migrações SQL versionadas, anonimização da conta, auditoria (escritas + exportações + eventos de login; retenção de 1 ano para acesso e 5 anos para o resto) e cancelamento de venda pelo chat com motivo.
- **2026-11-18**: **migrações SQL versionadas** no lugar do `create_all`: `V001__estrutura_inicial.sql` (retrato dos models), executor com checksum, trava contra execução simultânea e transação por arquivo. Teste de paridade migrações × models. Banco `gestao` (vazio) recriado pelas migrações.
- **2026-11-18**: **anonimização da conta** (`V002`: CPF/telefone anuláveis — 1ª migração incremental, aplicada sem recriar o banco). Nome vira "Usuário anonimizado", email `anonimizado-{id}@anonimizado.invalid`, CPF/telefone apagados, senha aleatória, sessões e ações do chat removidas, desvinculado da empresa; vendas/clientes continuam apontando para o registro. Dono não pode (409). Bug achado pelo teste e corrigido: refresh de conta desativada disparava "alerta de reuso" por email.
- **2026-11-18**: **auditoria** (`V003`, `services/auditoria_service.py`, `GET /auditoria`): escritas de produtos, estoque, clientes, vendas (cancelamento com motivo), empresa, cargos, convites e conta; exportações; login/falha/logout geral/reuso de token. Registro na mesma transação da operação. Origem `api`/`chat`. 132 testes.
- **2026-11-18**: **cancelar venda pelo chat** (`cancelar_venda`): motivo **obrigatório** (3–60 caracteres; o modelo pergunta se faltar), mesmas regras da API já na preparação (funcionário só as próprias, outra empresa = não encontrada, já cancelada = erro), prévia com itens/valor/data, execução só na confirmação, auditoria com origem `chat`. Cadastro de clientes pelo chat: **não** (decisão do usuário: manual, mais atenção).
- **Próximos passos sugeridos:**
  1. ~~Relatório de produtos~~ ✅ · ~~Previsão v1~~ ✅ · ~~Chat (leitura)~~ ✅
  2. ~~Ações com confirmação no chat~~ ✅
  3. Envio de email (transparência LGPD: troca de senha/email) e rotas de direitos do titular.
  4. Frontend Angular.
  5. Previsão v2 (se os dados justificarem): backtest da v1 (erro médio por produto) antes de trocar de modelo; previsão de preço/margem.

## 🗺️ Mapa de rotas (REST)

**Todas as rotas ficam sob `/api/v1`** (ex.: `POST /api/v1/auth/login`). A tabela abaixo omite o prefixo.

| Recurso | Rotas |
|---|---|
| Auth | `POST /auth/login` (form: username/password) · `POST /auth/refresh` · `POST /auth/logout` · `POST /auth/logout-geral` (os três com `{"refresh_token"}`) |
| Usuários | `POST /usuarios` (cadastro) · `GET /usuarios/me` · `PATCH /usuarios/me` · `GET /usuarios/me/dados` (exportar meus dados) · `POST /usuarios/me/anonimizacao` (`{"senha"}`) · `POST /convites/aceitar` (`{"token"}`) |
| Empresa (a do usuário logado) | `POST /empresa` · `GET /empresa` · `PATCH /empresa` · `GET /empresa/funcionarios` · `POST /empresa/funcionarios/busca` · `PATCH /empresa/funcionarios/{id}` (cargo) · `DELETE /empresa/funcionarios/{id}` (desvincula) · `POST /empresa/convites` |
| Clientes | `POST /clientes` · `GET /clientes?usuario_id=&periodo=` · `POST /clientes/busca` (nome/email/cpf/telefone no corpo) · `GET/PATCH/DELETE /clientes/{id}` |
| Produtos | `POST /produtos` · `GET /produtos?nome=&codigo_produto=&abaixo_estoque_min=&periodo=` · `GET/PATCH/DELETE /produtos/{id}` · `POST /produtos/{id}/reposicao` |
| Vendas | `POST /vendas` · `GET /vendas?usuario_id=&cliente_id=&status=&forma_pagamento=&periodo=` · `GET /vendas/{id}` · `POST /vendas/{id}/cancelar` |
| Previsões (dono e admin) | `GET /previsoes/produtos/{id}?dias=30` · `GET /previsoes/reposicao?prazo_entrega=7&dias_cobertura=30&apenas_necessarios=true` |
| Assistente | `POST /chat` (`{"mensagem", "historico": [{"papel": "usuario"/"assistente", "conteudo"}]}` → `{"resposta", "ferramentas_usadas", "acoes_pendentes"}`) · `POST /chat/acoes/{id}/confirmar` · `DELETE /chat/acoes/{id}` (cancelar) |
| Auditoria (só dono) | `GET /auditoria?categoria=&acao=&entidade=&entidade_id=&usuario_id=&origem=&periodo=` |
| Relatórios | `GET /relatorios/vendas` · `GET /relatorios/vendas/exportar` (só dono) · `GET /relatorios/produtos` · `GET /relatorios/produtos/exportar` (dono e admin) |

Em todas as listagens: `?limite=50&offset=0` e filtro de data `?periodo=mes|semestre|ano` **ou** `?data_inicial=&data_final=`.

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
- [x] Limpeza de dados vencidos agendada (ao iniciar + a cada `LIMPEZA_INTERVALO_HORAS`, padrão 24 h)
- [x] Email de aviso: troca de senha, troca de email (antigo e novo) e sessão comprometida. Backend `console` em dev; SMTP via `.env`
- [x] Direitos do titular: exportar "meus dados" (`GET /usuarios/me/dados`)
- [x] Direitos do titular: anonimizar a própria conta (`POST /usuarios/me/anonimizacao`)
- [ ] Transferência de dono (hoje o dono não pode anonimizar a conta enquanto for dono)
- [x] Limite de login: 5 falhas em 15 min por (IP + email) → 429 com Retry-After
- [ ] Limite de login está em memória (por processo): com vários workers/servidores, trocar por Redis; atrás de proxy, `uvicorn --proxy-headers`
- [x] Relatório de produtos
- [ ] Margem por produto usa o faturamento **bruto** (o desconto é da venda inteira, não de cada item). Se precisar: ratear o desconto entre os itens
- [ ] Empresa: desativar/excluir; transferência de dono
- [ ] Busca de produto por nome usa `LIKE '%x%'` (não usa índice). Se o volume crescer: `pg_trgm`
- [ ] Ollama: manter atualizado (`winget upgrade Ollama.Ollama`); **nunca expor a porta 11434** (sem `OLLAMA_HOST=0.0.0.0`). Em produção, rodar no mesmo servidor da API, preso ao localhost ou numa rede privada. A API do Ollama não tem autenticação (por projeto); as CVEs de 2026 (ex.: CVE-2026-7482 "Bleeding Llama") foram exploradas em servidores expostos

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
- **2026-11-18**: rotas no padrão REST, a pedido do usuário. Decisões:
  - Recursos no plural, com o verbo HTTP indicando a ação. `/empresa` no singular porque cada usuário tem no máximo uma (é sempre "a minha").
  - Listar, buscar e "por funcionário" viraram **um GET com filtros** (`?usuario_id=`). Menos rotas para o Angular manter.
  - **Busca com dado pessoal (nome/email/CPF/telefone) via `POST …/busca`**, com os filtros no corpo: dado pessoal não vai para a URL nem para os logs (regra LGPD do CLAUDE.md). Produtos não têm dado pessoal, então os filtros ficam no GET.
  - Ações que não são CRUD viram sub-recursos: `POST /vendas/{id}/cancelar` (venda não se edita nem se apaga: é histórico financeiro) e `POST /produtos/{id}/reposicao`.
  - `/auth/*` reúne login e tokens. O token do convite vai no corpo, não na URL (é um segredo).
  - Novas: `GET /empresa` e `GET /vendas/{id}`; filtros `status`, `forma_pagamento` e `cliente_id` em vendas.
- **2026-11-18**: relatório de produtos, base para a IA de previsão. Decisões:
  - `custo_unitario` gravado em cada item da venda: a margem histórica não muda quando o preço de compra do produto muda.
  - **1 consulta** (produtos LEFT JOIN vendas agregadas por produto) e o resto em pandas. Troca: traz uma linha por produto (volume moderado) em vez de ~8 consultas.
  - Inclui produtos desativados que venderam no período, para o faturamento bater com o relatório de vendas. O resumo de estoque conta só os ativos.
  - Média diária = vendido ÷ dias do período (do filtro, ou da 1ª venda até agora). `dias_estoque` = estoque ÷ média: é a semente da previsão de reposição que a IA vai refinar.
  - JSON enxuto (resumo + top 10 + reposição); a tabela completa por produto só no Excel, para manter a resposta leve.
  - Dono e admin acessam (é operacional); o relatório de vendas continua só do dono (tem nomes de clientes e de funcionários).
  - LGPD: o relatório de produtos não tem dado pessoal.
- **2026-11-18**: previsão v1. Decisões:
  - **Sem LLM e sem biblioteca pesada** (Prophet/statsmodels): pandas resolve, é rápido, explicável e testável. LangChain/LlamaIndex ficam para os agentes, onde há linguagem natural.
  - Método: média móvel de 7 dias (tira o ciclo semanal) + média exponencial com meia-vida de 14 dias (o recente pesa mais) × fator do dia da semana (só com ≥ 28 dias de histórico). Incerteza pelo desvio-padrão diário: intervalo de ~80% e estoque de segurança de ~95%.
  - O histórico termina **ontem** (hoje está incompleto e puxaria a previsão para baixo). Dias antes de o produto existir valem "sem dado" (NaN), não "zero venda".
  - "Dia" no fuso da empresa (`FUSO_HORARIO`, padrão America/Sao_Paulo). O filtro do SQL usa `created_at` puro (aproveita o índice) e a conversão de fuso só no GROUP BY.
  - **2 consultas**, qualquer que seja o nº de produtos; cálculo vetorizado (~0,1 s com 2.000 produtos, ~0,5 s com 10.000).
  - Reposição: compra = demanda(prazo + cobertura) + segurança − estoque, nunca abaixo do mínimo; urgência `comprar_agora` / `em_breve` / `ok`; ordenada pela ruptura mais próxima.
  - `confianca` (baixa/média/alta) por dias de histórico e volume: o frontend deve mostrar isso junto com o número.
  - Dono e admin (envolve custo de compra). LGPD: só quantidades e datas.
- **2026-11-18**: pedido do usuário: valor de reposição **não pode parecer exato** (o preço de compra varia). O resumo da reposição passou a priorizar o **nível de necessidade** (`por_necessidade`: quantos produtos em `comprar_agora` / `em_breve` / `ok`); o campo `urgencia` virou `necessidade`; o total virou `gasto_estimado_reposicao`. Regra geral: todo valor projetado em dinheiro é rotulado como estimativa (também nas respostas do chat).
- **2026-11-18**: assistente via chat. Decisões:
  - **Ollama local** (escolha do usuário; "se ficar ruim, a gente troca"). Com o modelo local, nenhum dado sai da máquina. Trocar de modelo = `OLLAMA_MODELO` no `.env`.
  - **Laço de ferramentas próprio** com `langchain-core` + `langchain-ollama` (sem LangGraph): controle de passos (máx. 5), erros e tempo; o modelo é injetado como dependência, então os testes usam um **modelo roteirizado** (`tests/modelo_falso.py`).
  - `qwen3` com `reasoning=False` (sem modo pensamento: muito mais rápido), `temperature=0`, `keep_alive=30m`.
  - Ferramentas chamam os services **com o usuário logado** → permissões e isolamento valem no chat. Erros (permissão, 404, argumento inválido) voltam ao modelo como `{"erro": ...}` para ele explicar.
  - **Histórico no frontend** (o servidor não guarda conversas), no máximo 10 mensagens.
  - **Lição do teste real:** formato "colunas + linhas" fez o qwen3:8b desalinhar valores ("comprar 1" em vez de 4). Ferramentas usam **objetos com chaves curtas**; campo sem valor (ex.: sem data de ruptura) é **omitido** para o modelo não inventar.
  - LGPD: ferramentas nunca entregam CPF/email/telefone; cliente aparece como "Maria S."; o conteúdo das mensagens não é logado.
- **2026-11-18**: ações de escrita no chat. Decisões:
  - O modelo **nunca executa**: a ferramenta valida, mostra uma prévia ("Venda: 3× Café (R$ 76,50) · pix · total R$ 75,00") e cria uma ação pendente. A **execução é determinística** (rota de confirmação → service), sem passar pelo modelo.
  - Só quem pediu confirma (nem o dono da mesma empresa). Validade de 10 min; expirada → 410 e apagada; a rotina de retenção limpa as vencidas.
  - A ação é apagada **na mesma transação** da execução: se falhar (ex.: estoque mudou → 409), ela continua e dá para cancelar; se der certo, não executa duas vezes (`FOR UPDATE` contra duplo clique).
  - As permissões são checadas de novo na confirmação (quem perdeu o cargo no meio recebe 403).
  - **Lição do teste real nº 2:** o qwen3:8b inventou um `produto_id` em vez de buscar antes. As ferramentas passaram a receber **nome (ou código) do produto e nome do cliente** e resolvem por dentro. Nome ambíguo → erro com as opções, para o modelo perguntar ao usuário.
  - **Lição nº 3:** citar o botão "Confirmar" no prompt fazia o modelo mencioná-lo até em consultas. A instrução de confirmação só vem na resposta da ferramenta de escrita (`situacao`).
- **2026-11-18**: segurança do Ollama. A falta de senha na API não é um bug "a corrigir": é de projeto. A proteção é a configuração (escutar só no localhost) + o firewall como segunda camada. O Angular nunca fala direto com o Ollama, só com o backend.
- **2026-11-18**: discussão de próximos passos com o usuário:
  - Cadastro de clientes fica **manual** (mais atenção, menos risco). Cancelar venda pelo chat: sim, com **motivo obrigatório** e confirmação.
  - **Auditoria**: registrar escritas (criar/editar/excluir, vendas, estoque, cargos, convites, conta). GETs não, **exceto**: exportações (Excel e "meus dados": saída de dado pessoal em massa) e eventos de segurança (login, falha de login, reuso de token). O log também é dado pessoal: guardar quem/o quê/quando/origem/campos alterados (CPF/email/telefone/senha só como "alterado"); retenção proposta: 1 ano (acesso) e 5 anos (vendas, possível exigência fiscal); só o dono consulta; ninguém edita/apaga.
  - **Migrações**: o usuário propôs SQL puro versionado (estrutura e dados) e versionamento da API (v1 → v2 com período de transição). Proposta: arquivos `V001__x.sql` + tabela `schema_versao` (estilo Flyway), ORM só para as consultas, teste que compara o banco migrado com os models; `/api/v1` agora; mudanças incompatíveis no padrão **expandir e contrair** (a v1 recebe os cabeçalhos `Deprecation`/`Sunset` até sair).
- **2026-11-18**: migrações. Decisões:
  - Executor próprio (~100 linhas) em vez de Flyway/Alembic: SQL puro como o usuário pediu, sem dependência nova.
  - Checksum SHA-256 com quebras de linha normalizadas (o git no Windows troca `
` por `

`).
  - `pg_advisory_lock`: dois servidores subindo juntos não migram ao mesmo tempo.
  - Cada arquivo roda numa transação (o Postgres desfaz até DDL): uma falha não deixa o banco pela metade.
  - Recusa banco "criado sem migrações" (tem tabelas e não tem `schema_versao`) em vez de tentar adivinhar o estado.
  - O `V001` foi gerado uma vez pelo DDL dos models. A paridade é garantida por teste: cria um banco pelos models, outro pelas migrações, e compara colunas, tipos, nulos, índices, unicidades e FKs.
- **2026-11-18**: auditoria. Decisões:
  - `registrar()` só faz `db.add()`: entra na **mesma transação** da operação (falhou → sem log; deu certo → os dois juntos). Custo: 1 INSERT por escrita.
  - **Categorias** definem a retenção: `acesso` (login, falhas, exportações, conta) = 1 ano; `operacao` e `venda` = 5 anos. DELETE pelo índice `(categoria, created_at)` na limpeza diária.
  - LGPD: em entidades pessoais (usuário, cliente) os campos alterados aparecem só como "alterado"; senha nunca. **IP só em eventos de acesso** e **fora da resposta da API**. Falha de login com email inexistente **não guarda o email digitado**.
  - Origem `chat` via `ContextVar` na confirmação das ações: os services não precisaram mudar de assinatura.
  - Dinheiro guardado como texto (`"30.00"`), não float.
  - Só o dono consulta (admin não); nenhuma rota edita ou apaga a trilha.
- **2026-11-18**: regra combinada: **um commit por alteração**, no formato `tipo: descrição` (feat, fix, refactor, test, docs, chore).
