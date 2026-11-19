"""LGPD — retenção: dados que perderam a finalidade são apagados."""
from datetime import datetime, timedelta, timezone
from main import limpar_dados_expirados
from tests.fabrica import gerar_convite, login


def test_limpa_tokens_e_convites_vencidos(client, loja, db):
    from models.refresh_token import RefreshToken
    from models.convite_funcionario import Convite

    login(client, loja.dono.email)
    gerar_convite(client, loja.dono.headers)
    passado = datetime.now(timezone.utc) - timedelta(days=1)
    vencido = db.query(RefreshToken).first()
    vencido.expires_at = passado
    db.query(Convite).update({'expires_at': passado})
    db.commit()
    tokens_antes = db.query(RefreshToken).count()

    limpar_dados_expirados()

    db.expire_all()
    assert db.query(RefreshToken).count() == tokens_antes - 1
    assert db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.now(timezone.utc)).count() == 0
    assert db.query(Convite).count() == 0


def test_rotina_agendada_repete_a_limpeza(client, loja, db):
    """Roda a rotina com intervalo curtíssimo e confere que ela limpou sozinha."""
    import asyncio
    from models.convite_funcionario import Convite
    from main import rotina_limpeza

    gerar_convite(client, loja.dono.headers)
    db.query(Convite).update({'expires_at': datetime.now(timezone.utc) - timedelta(days=1)})
    db.commit()

    async def rodar_um_pouco():
        tarefa = asyncio.create_task(rotina_limpeza(0.05 / 3600))  # a cada 0,05 s
        await asyncio.sleep(0.3)
        tarefa.cancel()

    asyncio.run(rodar_um_pouco())
    db.expire_all()
    assert db.query(Convite).count() == 0
