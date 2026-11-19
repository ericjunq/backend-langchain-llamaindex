"""Infraestrutura dos testes.

Os testes rodam num banco Postgres SEPARADO (mesmo servidor do .env, com o nome
trocado para `<banco>_teste`, ou o que estiver em TEST_DATABASE_URL). O banco é
criado no início e apagado no fim. O banco de desenvolvimento nunca é tocado.
"""
import os
import pytest
import psycopg
from sqlalchemy import text
from sqlalchemy.engine import make_url

# --- Aponta a aplicação para o banco de teste ANTES de importar database/main ---
from security.settings import settings

_url = make_url(os.environ.get('TEST_DATABASE_URL') or settings.database_url)
if not (_url.database or '').endswith('_teste'):
    _url = _url.set(database=f'{_url.database}_teste')
assert _url.database.endswith('_teste'), 'Proteção: os testes só rodam em banco terminado em _teste'
settings.database_url = _url.render_as_string(hide_password=False)

def _admin_conn():
    """Conexão no banco 'postgres' do mesmo servidor, para criar/apagar o banco de teste."""
    return psycopg.connect(
        host=_url.host or 'localhost', port=_url.port or 5432,
        user=_url.username, password=_url.password,
        dbname='postgres', autocommit=True,
    )

with _admin_conn() as _c:
    _c.execute(f'DROP DATABASE IF EXISTS "{_url.database}" WITH (FORCE)')
    _c.execute(f'CREATE DATABASE "{_url.database}"')

import database  # noqa: E402  (precisa vir depois do ajuste da URL)
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TABELAS = ', '.join(t.name for t in database.Base.metadata.sorted_tables)


@pytest.fixture(scope='session')
def client():
    # O lifespan do app roda create_all no banco de teste.
    # base_url com /api/v1: os testes usam caminhos relativos ('/produtos') e batem na versão atual.
    with TestClient(main.app, base_url=f'http://testserver{main.API_V1}') as c:
        yield c
    database.engine.dispose()
    with _admin_conn() as c:
        c.execute(f'DROP DATABASE IF EXISTS "{_url.database}" WITH (FORCE)')


@pytest.fixture(autouse=True)
def banco_limpo(client):
    """Cada teste começa com as tabelas vazias (TRUNCATE é bem mais rápido que recriar)
    e com a caixa de emails vazia."""
    from services import email_service
    from security.limite_tentativas import limite_login
    settings.email_backend = 'memoria'
    email_service.caixa_de_saida.clear()
    limite_login.resetar()
    yield
    with database.engine.begin() as conn:
        conn.execute(text(f'TRUNCATE {TABELAS} RESTART IDENTITY CASCADE'))


@pytest.fixture
def db():
    """Sessão direta no banco, para preparar cenários ou conferir o que foi gravado."""
    sessao = database.LocalSession()
    try:
        yield sessao
    finally:
        sessao.close()


@pytest.fixture
def modelo():
    """Troca o Ollama por um modelo roteirizado. Uso: m = modelo(passo1, passo2, ...)."""
    from services.chat_service import get_fabrica_modelo
    from tests.modelo_falso import ModeloRoteirizado
    atual = {}

    def instalar(*passos):
        atual['m'] = ModeloRoteirizado(*passos)
        main.app.dependency_overrides[get_fabrica_modelo] = lambda: atual['m']
        return atual['m']

    yield instalar
    main.app.dependency_overrides.pop(get_fabrica_modelo, None)


@pytest.fixture
def loja(client):
    from tests.fabrica import criar_loja
    return criar_loja(client)


@pytest.fixture
def outra_loja(client):
    from tests.fabrica import criar_loja
    return criar_loja(client)
