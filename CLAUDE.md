## Stack

Python + FastAPI + SQLAlchemy 2 + Pydantic v2 + PostgreSQL. Relatórios com pandas; fase de IA com LangChain/LlamaIndex. Estrutura do banco definida só pelos models do SQLAlchemy (`Base.metadata.create_all`), **sem migrações (sem Alembic)**. Como `create_all` não altera tabelas existentes, toda mudança de model exige recriar o banco (`drop_all` + `create_all`). Isso apaga os dados e por isso exige confirmação explícita do usuário.

## Prioridades permanentes (valem para toda decisão, em qualquer parte do sistema)

1. **Desempenho sempre priorizado.** Toda proposta, consulta, endpoint, comando ou mudança de modelo é pensada primeiro pelo custo: quantas consultas ao banco, se usa índice, quanto cresce com o volume, quanto pesa a resposta. Quando houver troca entre simplicidade e desempenho, explicar a troca e recomendar.
2. **LGPD em tudo, não só em pontos específicos.** Todo dado pessoal (de usuário/funcionário, dono de empresa ou cliente final) segue os princípios da lei:
   - **finalidade e necessidade:** coletar e guardar só o que tem uso claro;
   - **mínima exposição:** cada rota mostra só o necessário para quem a chama;
   - **segurança:** hash, tokens com validade, HTTPS, nada pessoal em URL ou log;
   - **retenção:** apagar ou anonimizar o que perdeu a finalidade;
   - **direitos do titular:** acesso, correção e anonimização;
   - **transparência:** avisos por email quando algo muda.

   Em toda proposta, dizer como a LGPD foi considerada, mesmo quando o assunto não parece envolver dados pessoais.

3. **Trilha de ideias para outro chat.** A cada nova ideia, implementação, alteração ou decisão, registrar no `CHECKLIST.md`: na seção "📍 Onde paramos" e na **"🧵 Trilha de ideias"**, que guarda o histórico curto do raciocínio (o que foi pensado, decidido e por quê). Uma conversa nova precisa conseguir seguir a mesma linha de ideias só lendo os guias.

## Regras de desenvolvimento combinadas com o usuário

### Comunicação

- **Respostas curtas e diretas** por padrão.
- **Explicar mais** quando o usuário pedir detalhes, quando perceber que ele não entendeu, em debates de ideias (planejamento, arquitetura, brainstorming) e quando houver **risco**: dados importantes (`migrate:fresh`, exclusões), decisões importantes de arquitetura ou API, ações difíceis de reverter. Nesses casos, explicar o porquê, as consequências e as alternativas.
- Escrever em português.

### Fluxo de trabalho

- **Plano antes de cada alteração:** antes de mexer em código, banco ou configuração, apresentar o plano de implementação (o que vai mudar, em quais arquivos, impacto em desempenho e LGPD) e só então executar.
- Ambiente local: PostgreSQL 18 em `localhost:5432`, banco `gestao` (credenciais no `.env`, fora do git). Testes usam um banco temporário separado (`gestao_teste`), apagado ao final.
- **Commits:** um commit a cada alteração concluída (com os testes passando), no formato `tipo: descrição` em português. Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`. O CHECKLIST.md atualizado entra no mesmo commit da alteração.
- **Rotas:** padrão REST (recursos no plural, verbo HTTP = ação). Dado pessoal nunca vai na URL: buscas por nome/email/CPF/telefone usam `POST …/busca`, com os filtros no corpo.
- **Testes:** `python -m pytest` (em `tests/`). Toda alteração de comportamento vem com teste novo ou ajustado, e a suíte precisa passar antes de dar a tarefa por concluída.
