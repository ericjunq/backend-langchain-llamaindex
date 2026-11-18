from datetime import datetime, timedelta, timezone
from tests.fabrica import gerar_convite, nova_conta, nova_empresa, vincular


def test_criar_empresa_torna_usuario_dono(client):
    conta = nova_conta(client)
    empresa = nova_empresa(client, conta.headers)
    me = client.get('/usuario/me', headers=conta.headers).json()
    assert me['cargo'] == 'dono' and me['empresa_id'] == empresa['id']


def test_nao_cria_segunda_empresa(client, loja):
    r = client.post('/empresa/criar_empresa', headers=loja.dono.headers, json={
        'nome': 'Outra', 'cnpj': '11222333000181', 'email': 'x@teste.com', 'telefone': '1133334444'})
    assert r.status_code == 400


def test_convite_vincula_como_funcionario(client, loja):
    me = client.get('/usuario/me', headers=loja.func.headers).json()
    assert me['cargo'] == 'funcionario'
    assert me['empresa_id'] == loja.empresa['id']


def test_so_dono_gera_convite(client, loja):
    assert client.post('/empresa/gerar_convite', headers=loja.func.headers).status_code == 403


def test_convite_usado_expirado_ou_invalido(client, loja, db):
    from models.convite_funcionario import Convite

    token = gerar_convite(client, loja.dono.headers)
    assert vincular(client, nova_conta(client).headers, token).status_code == 200
    assert vincular(client, nova_conta(client).headers, token).status_code == 409

    expirado = gerar_convite(client, loja.dono.headers)
    db.query(Convite).filter(Convite.token == expirado).update(
        {'expires_at': datetime.now(timezone.utc) - timedelta(minutes=1)})
    db.commit()
    assert vincular(client, nova_conta(client).headers, expirado).status_code == 410

    assert vincular(client, nova_conta(client).headers, 'nao-existe').status_code == 404


def test_quem_ja_tem_empresa_nao_usa_convite(client, loja):
    token = gerar_convite(client, loja.dono.headers)
    assert vincular(client, loja.func.headers, token).status_code == 403


def test_editar_cargo(client, loja):
    url = f'/empresa/editar_cargo_funcionario/{loja.func.id}'
    assert client.patch(url, headers=loja.func.headers, json={'cargo': 'admin'}).status_code == 403
    assert client.patch(f'/empresa/editar_cargo_funcionario/{loja.dono.id}', headers=loja.dono.headers,
                        json={'cargo': 'admin'}).status_code == 403  # não altera o próprio cargo
    r = client.patch(url, headers=loja.dono.headers, json={'cargo': 'admin'})
    assert r.status_code == 200 and r.json()['cargo'] == 'admin'
    assert client.patch(url, headers=loja.dono.headers, json={'cargo': 'dono'}).status_code == 422


def test_remover_funcionario_corta_acesso_na_hora(client, loja):
    assert client.get('/produtos/listar_produtos', headers=loja.func.headers).status_code == 200
    r = client.patch(f'/empresa/remover_funcionario/{loja.func.id}', headers=loja.dono.headers)
    assert r.status_code == 200 and r.json()['empresa_id'] is None
    # O mesmo access token não acessa mais a empresa.
    assert client.get('/produtos/listar_produtos', headers=loja.func.headers).status_code == 403


def test_dono_nao_remove_a_si_mesmo(client, loja):
    r = client.patch(f'/empresa/remover_funcionario/{loja.dono.id}', headers=loja.dono.headers)
    assert r.status_code == 403


def test_editar_empresa_so_dono(client, loja):
    assert client.patch('/empresa/editar_empresa', headers=loja.func.headers,
                        json={'telefone': '1144445555'}).status_code == 403
    assert client.patch('/empresa/editar_empresa', headers=loja.dono.headers,
                        json={'telefone': '1144445555'}).status_code == 200


def test_listar_funcionarios_paginado(client, loja):
    r = client.get('/empresa/listar_funcionarios', headers=loja.dono.headers)
    assert {u['id'] for u in r.json()} == {loja.dono.id, loja.func.id}
    assert len(client.get('/empresa/listar_funcionarios?limite=1', headers=loja.dono.headers).json()) == 1
    assert client.get('/empresa/listar_funcionarios?limite=500', headers=loja.dono.headers).status_code == 422
