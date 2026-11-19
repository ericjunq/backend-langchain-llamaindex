"""Migrações SQL versionadas: executor e paridade com os models."""
import pytest
from sqlalchemy import create_engine, inspect

import database
import migracoes
from tests.conftest import _admin_conn, _url


@pytest.fixture
def banco_temporario():
    """Cria um banco vazio só para o teste e apaga no fim."""
    criados = []

    def criar(sufixo: str):
        nome = f'{_url.database}_{sufixo}'
        with _admin_conn() as c:
            c.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')
            c.execute(f'CREATE DATABASE "{nome}"')
        engine = create_engine(_url.set(database=nome))
        criados.append((nome, engine))
        return engine

    yield criar
    for nome, engine in criados:
        engine.dispose()
        with _admin_conn() as c:
            c.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _retrato(engine) -> dict:
    insp = inspect(engine)
    retrato = {}
    for tabela in sorted(set(insp.get_table_names()) - {'schema_versao'}):
        retrato[tabela] = {
            'colunas': {c['name']: (str(c['type']), c['nullable'], str(c.get('default'))) for c in insp.get_columns(tabela)},
            'pk': insp.get_pk_constraint(tabela)['constrained_columns'],
            'indices': sorted((i['name'], tuple(i['column_names']), bool(i['unique'])) for i in insp.get_indexes(tabela)),
            'unicos': sorted(tuple(u['column_names']) for u in insp.get_unique_constraints(tabela)),
            'fks': sorted((tuple(f['constrained_columns']), f['referred_table']) for f in insp.get_foreign_keys(tabela)),
        }
    return retrato


def test_migracoes_produzem_exatamente_os_models(banco_temporario):
    """Se alguém mudar um model e esquecer a migração (ou o contrário), este teste falha."""
    pelos_models = banco_temporario('modelos')
    database.Base.metadata.create_all(pelos_models)
    pelas_migracoes = database.engine  # banco de teste: criado pelas migrações no início da sessão

    esperado, obtido = _retrato(pelos_models), _retrato(pelas_migracoes)
    assert obtido.keys() == esperado.keys()
    for tabela in esperado:
        assert obtido[tabela] == esperado[tabela], f'tabela {tabela} diverge entre migrações e models'


def test_executor(banco_temporario, tmp_path):
    engine = banco_temporario('mig')
    (tmp_path / 'V001__cria_a.sql').write_text('CREATE TABLE a (id INT);\nINSERT INTO a VALUES (1);', encoding='utf-8')

    assert migracoes.aplicar(engine, tmp_path) == ['V001__cria_a']
    assert migracoes.aplicar(engine, tmp_path) == []  # idempotente

    (tmp_path / 'V002__cria_b.sql').write_text('CREATE TABLE b (id INT);', encoding='utf-8')
    assert migracoes.aplicar(engine, tmp_path) == ['V002__cria_b']
    assert migracoes.estado(engine, tmp_path) == [('V001__cria_a', True), ('V002__cria_b', True)]

    # Mesma migração com quebras de linha do Windows: não conta como alteração.
    (tmp_path / 'V001__cria_a.sql').write_bytes(b'CREATE TABLE a (id INT);\r\nINSERT INTO a VALUES (1);')
    assert migracoes.aplicar(engine, tmp_path) == []

    # Editar uma migração já aplicada é recusado.
    (tmp_path / 'V001__cria_a.sql').write_text('CREATE TABLE a (id BIGINT);', encoding='utf-8')
    with pytest.raises(migracoes.ErroMigracao, match='alterada depois de aplicada'):
        migracoes.aplicar(engine, tmp_path)


def test_migracao_com_erro_e_desfeita_por_inteiro(banco_temporario, tmp_path):
    engine = banco_temporario('mig')
    (tmp_path / 'V001__quebrada.sql').write_text('CREATE TABLE c (id INT);\nSELECT coluna_que_nao_existe;', encoding='utf-8')
    with pytest.raises(migracoes.ErroMigracao, match='Falha ao aplicar V001__quebrada'):
        migracoes.aplicar(engine, tmp_path)
    assert not inspect(engine).has_table('c')  # nada pela metade
    assert migracoes.estado(engine, tmp_path) == [('V001__quebrada', False)]


def test_recusa_banco_criado_sem_migracoes(banco_temporario, tmp_path):
    engine = banco_temporario('mig')
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE usuarios (id INT)')
    (tmp_path / 'V001__x.sql').write_text('SELECT 1;', encoding='utf-8')
    with pytest.raises(migracoes.ErroMigracao, match='não tem controle de versão'):
        migracoes.aplicar(engine, tmp_path)


def test_nome_fora_do_padrao(tmp_path):
    (tmp_path / '001_sem_v.sql').write_text('SELECT 1;', encoding='utf-8')
    with pytest.raises(migracoes.ErroMigracao, match='fora do padrão'):
        migracoes.listar(tmp_path)
