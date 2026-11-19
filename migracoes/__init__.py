"""Migrações versionadas em SQL puro (estilo Flyway).

- Arquivos `VNNN__descricao.sql` nesta pasta, aplicados em ordem, cada um na sua transação
  (estrutura e/ou dados). Registro em `schema_versao` (versão, nome, checksum, data).
- Nunca editar um arquivo já aplicado: o checksum muda e a aplicação é recusada. Para corrigir,
  crie um novo arquivo.
- Trava (`pg_advisory_lock`): se dois servidores sobem juntos, só um migra; o outro espera.
- Mudança incompatível com a versão da API em uso → padrão "expandir e contrair":
  V00N adiciona o novo sem remover o velho; depois que a versão antiga da API sair, outro
  arquivo remove o que sobrou.

Uso: automático ao subir a API, ou `python -m migracoes` (aplica e mostra o estado).
"""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, inspect

PASTA = Path(__file__).parent
PADRAO = re.compile(r'^V(\d{3,})__([a-z0-9_]+)\.sql$')
CHAVE_TRAVA = 7_270_001  # número arbitrário e fixo para o pg_advisory_lock

TABELA_VERSAO = """
CREATE TABLE IF NOT EXISTS schema_versao (
    versao      INTEGER PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    checksum    CHAR(64) NOT NULL,
    aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now()
)"""


class ErroMigracao(RuntimeError):
    pass


@dataclass(frozen=True)
class Migracao:
    versao: int
    nome: str
    sql: str

    @property
    def checksum(self) -> str:
        # Normaliza quebras de linha: o git no Windows pode trocar \n por \r\n no checkout.
        return hashlib.sha256(self.sql.replace('\r\n', '\n').encode('utf-8')).hexdigest()


def listar(pasta: Path = PASTA) -> list[Migracao]:
    migracoes = []
    for arquivo in pasta.glob('*.sql'):
        m = PADRAO.match(arquivo.name)
        if not m:
            raise ErroMigracao(f'Nome fora do padrão VNNN__descricao.sql: {arquivo.name}')
        migracoes.append(Migracao(int(m.group(1)), arquivo.stem, arquivo.read_text(encoding='utf-8')))
    migracoes.sort(key=lambda m: m.versao)
    versoes = [m.versao for m in migracoes]
    if len(versoes) != len(set(versoes)):
        raise ErroMigracao('Há duas migrações com o mesmo número de versão')
    return migracoes


def aplicar(engine: Engine, pasta: Path = PASTA) -> list[str]:
    """Aplica as migrações pendentes. Devolve os nomes das que foram aplicadas agora."""
    migracoes = listar(pasta)
    aplicadas_agora = []

    with engine.connect() as conn:
        conn.exec_driver_sql(f'SELECT pg_advisory_lock({CHAVE_TRAVA})')
        conn.commit()
        try:
            ja_existe_controle = inspect(conn).has_table('schema_versao')
            if not ja_existe_controle and inspect(conn).has_table('usuarios'):
                raise ErroMigracao(
                    'O banco já tem tabelas mas não tem controle de versão (foi criado sem migrações). '
                    'Recrie o banco vazio para aplicar as migrações desde a V001.')
            conn.exec_driver_sql(TABELA_VERSAO)
            conn.commit()

            registradas = dict(conn.exec_driver_sql('SELECT versao, checksum FROM schema_versao').all())
            conn.commit()

            for migracao in migracoes:
                if migracao.versao in registradas:
                    if registradas[migracao.versao].strip() != migracao.checksum:
                        raise ErroMigracao(f'{migracao.nome} foi alterada depois de aplicada. '
                                           'Não edite migrações aplicadas: crie uma nova.')
                    continue
                try:
                    conn.exec_driver_sql(migracao.sql)
                    conn.exec_driver_sql(
                        'INSERT INTO schema_versao (versao, nome, checksum) VALUES (%s, %s, %s)',
                        (migracao.versao, migracao.nome, migracao.checksum))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise ErroMigracao(f'Falha ao aplicar {migracao.nome}: {e}') from e
                aplicadas_agora.append(migracao.nome)
        finally:
            conn.rollback()
            conn.exec_driver_sql(f'SELECT pg_advisory_unlock({CHAVE_TRAVA})')
            conn.commit()

    return aplicadas_agora


def estado(engine: Engine, pasta: Path = PASTA) -> list[tuple[str, bool]]:
    with engine.connect() as conn:
        registradas = set()
        if inspect(conn).has_table('schema_versao'):
            registradas = {v for (v,) in conn.exec_driver_sql('SELECT versao FROM schema_versao')}
    return [(m.nome, m.versao in registradas) for m in listar(pasta)]
