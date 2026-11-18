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
