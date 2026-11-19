from tests.fabrica import SENHA, dados_usuario, login, nova_conta


def test_cadastro_normaliza_dados_e_nao_expoe_dados_pessoais(client, db):
    from models.usuario_model import Usuarios
    dados = dados_usuario(email='Fulano@Teste.COM', telefone='(11) 98888-7777')
    dados['cpf'] = f'{dados["cpf"][:3]}.{dados["cpf"][3:6]}.{dados["cpf"][6:9]}-{dados["cpf"][9:]}'

    r = client.post('/usuarios', json=dados)

    assert r.status_code == 201
    corpo = r.json()
    assert not {'email', 'cpf', 'telefone', 'senha', 'senha_hash'} & corpo.keys()  # mínima exposição
    usuario = db.get(Usuarios, corpo['id'])
    assert usuario.email == 'fulano@teste.com'
    assert usuario.telefone == '11988887777'
    assert usuario.cpf.isdigit() and len(usuario.cpf) == 11
    assert usuario.senha_hash != SENHA


def test_cadastro_duplicado_ignora_maiusculas(client):
    conta = nova_conta(client)
    r = client.post('/usuarios', json=dados_usuario(email=conta.email.upper()))
    assert r.status_code == 409


def test_cadastro_valida_senha_e_cpf(client):
    assert client.post('/usuarios', json=dados_usuario(senha='curta')).status_code == 422
    assert client.post('/usuarios', json=dados_usuario(cpf='11111111111')).status_code == 422


def test_login_nao_revela_se_email_existe(client):
    conta = nova_conta(client)
    inexistente = login(client, 'ninguem@teste.com')
    senha_errada = login(client, conta.email, 'senhaerrada')
    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json()


def test_rotas_protegidas_exigem_access_token_valido(client):
    conta = nova_conta(client)
    assert client.get('/usuarios/me').status_code == 401
    assert client.get('/usuarios/me', headers={'Authorization': 'Bearer lixo'}).status_code == 401
    refresh_como_access = {'Authorization': f"Bearer {conta.tokens['refresh_token']}"}
    assert client.get('/usuarios/me', headers=refresh_como_access).status_code == 401
    assert client.get('/usuarios/me', headers=conta.headers).json()['id'] == conta.id


def test_refresh_rotaciona_e_detecta_reuso(client):
    conta = nova_conta(client)
    antigo = conta.tokens['refresh_token']

    r = client.post('/auth/refresh', json={'refresh_token': antigo})
    assert r.status_code == 200
    novo = r.json()['refresh_token']
    assert novo != antigo

    # Reusar o antigo = possível roubo: derruba todas as sessões, inclusive a nova.
    assert client.post('/auth/refresh', json={'refresh_token': antigo}).status_code == 401
    assert client.post('/auth/refresh', json={'refresh_token': novo}).status_code == 401


def test_refresh_rejeita_access_token(client):
    conta = nova_conta(client)
    r = client.post('/auth/refresh', json={'refresh_token': conta.tokens['access_token']})
    assert r.status_code == 401


def test_logout_e_logout_geral(client):
    conta = nova_conta(client)
    segunda_sessao = login(client, conta.email).json()

    assert client.post('/auth/logout', json={'refresh_token': conta.tokens['refresh_token']}).status_code == 200
    assert client.post('/auth/refresh', json={'refresh_token': conta.tokens['refresh_token']}).status_code == 401

    terceira = login(client, conta.email).json()
    assert client.post('/auth/logout-geral', json={'refresh_token': terceira['refresh_token']}).status_code == 200
    assert client.post('/auth/refresh', json={'refresh_token': segunda_sessao['refresh_token']}).status_code == 401


def test_troca_de_senha_exige_senha_atual_e_encerra_sessoes(client):
    conta = nova_conta(client)

    sem_atual = client.patch('/usuarios/me', headers=conta.headers, json={'senha': 'novasenha123'})
    assert sem_atual.status_code == 401

    ok = client.patch('/usuarios/me', headers=conta.headers,
                      json={'senha': 'novasenha123', 'senha_atual': SENHA})
    assert ok.status_code == 200
    assert client.post('/auth/refresh', json={'refresh_token': conta.tokens['refresh_token']}).status_code == 401
    assert login(client, conta.email).status_code == 401
    assert login(client, conta.email, 'novasenha123').status_code == 200


def test_editar_email_para_um_ja_usado(client):
    a, b = nova_conta(client), nova_conta(client)
    r = client.patch('/usuarios/me', headers=a.headers, json={'email': b.email, 'senha_atual': SENHA})
    assert r.status_code == 409


def test_limite_de_tentativas_de_login(client):
    conta = nova_conta(client)
    for _ in range(5):
        assert login(client, conta.email, 'errada').status_code == 401
    bloqueado = login(client, conta.email, SENHA)  # nem a senha certa passa enquanto bloqueado
    assert bloqueado.status_code == 429 and int(bloqueado.headers['retry-after']) > 0

    outra = nova_conta(client)
    assert login(client, outra.email).status_code == 200  # o bloqueio é por (IP + email), não geral


def test_login_certo_zera_as_falhas(client):
    conta = nova_conta(client)
    for _ in range(4):
        login(client, conta.email, 'errada')
    assert login(client, conta.email).status_code == 200
    for _ in range(4):
        assert login(client, conta.email, 'errada').status_code == 401  # contagem recomeçou


def test_rotas_estao_versionadas_em_api_v1(client):
    conta = nova_conta(client)
    assert client.get('http://testserver/api/v1/usuarios/me', headers=conta.headers).status_code == 200
    assert client.get('http://testserver/usuarios/me', headers=conta.headers).status_code == 404  # sem versão
    assert client.get('http://testserver/openapi.json').json()['components']['securitySchemes'][
        'OAuth2PasswordBearer']['flows']['password']['tokenUrl'] == '/api/v1/auth/login'
