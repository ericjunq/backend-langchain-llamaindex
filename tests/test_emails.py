"""LGPD — transparência: avisos por email quando algo muda na conta."""
import logging
from services import email_service
from security.settings import settings
from tests.fabrica import SENHA, login, nova_conta


def _caixa():
    return email_service.caixa_de_saida


def test_aviso_de_troca_de_senha(client):
    conta = nova_conta(client)
    client.patch('/usuarios/me', headers=conta.headers, json={'senha': 'novasenha123', 'senha_atual': SENHA})
    assert [(e['para'], e['assunto']) for e in _caixa()] == [(conta.email, 'Sua senha foi alterada')]


def test_aviso_de_troca_de_email_vai_para_os_dois_enderecos(client):
    conta = nova_conta(client)
    client.patch('/usuarios/me', headers=conta.headers, json={'email': 'novo@teste.com', 'senha_atual': SENHA})
    assert sorted(e['para'] for e in _caixa()) == sorted([conta.email, 'novo@teste.com'])
    assert all('n***@teste.com' in e['corpo'] for e in _caixa())  # o corpo não traz o email completo


def test_sem_aviso_quando_nada_muda_ou_falha(client):
    conta = nova_conta(client)
    client.patch('/usuarios/me', headers=conta.headers, json={'senha': 'novasenha123', 'senha_atual': 'errada'})
    client.patch('/usuarios/me', headers=conta.headers, json={'telefone': '11977776666'})
    assert _caixa() == []


def test_alerta_de_sessao_comprometida(client):
    conta = nova_conta(client)
    antigo = conta.tokens['refresh_token']
    client.post('/auth/refresh', json={'refresh_token': antigo})
    client.post('/auth/refresh', json={'refresh_token': antigo})  # reuso
    assert [e['assunto'] for e in _caixa()] == ['Alerta de segurança: sessões encerradas']


def test_backend_console_nao_registra_email_completo(client, caplog):
    settings.email_backend = 'console'
    with caplog.at_level(logging.INFO, logger='email'):
        email_service.avisar_senha_alterada('Fulano', 'fulano.silva@teste.com')
    assert 'f***@teste.com' in caplog.text and 'fulano.silva' not in caplog.text
    assert _caixa() == []


def test_login_normal_nao_dispara_email(client):
    conta = nova_conta(client)
    login(client, conta.email)
    assert _caixa() == []
