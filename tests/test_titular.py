"""LGPD — direitos do titular."""
from tests.fabrica import criar_venda, login, nova_conta, renovar, sessao


def test_exportar_meus_dados(client, loja, db):
    from models.usuario_model import Usuarios
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)])
    login(client, loja.func.email)  # segunda sessão

    r = client.get('/usuarios/me/dados', headers=loja.func.headers)

    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    dados = r.json()
    eu = db.get(Usuarios, loja.func.id)
    assert dados['perfil']['cpf'] == eu.cpf and dados['perfil']['email'] == eu.email
    assert dados['perfil']['cargo'] == 'funcionario'
    assert dados['empresa']['id'] == loja.empresa['id']
    assert len(dados['sessoes_ativas']) == 2
    assert dados['atividade'] == {'vendas_registradas': 1, 'clientes_cadastrados': 1}
    texto = str(dados)
    assert 'senha_hash' not in texto and eu.senha_hash not in texto  # hash não sai


def test_exportar_sem_empresa_e_so_os_proprios_dados(client, loja):
    conta = nova_conta(client)
    dados = client.get('/usuarios/me/dados', headers=conta.headers).json()
    assert dados['empresa'] is None and dados['perfil']['id'] == conta.id
    assert dados['atividade'] == {'vendas_registradas': 0, 'clientes_cadastrados': 0}
    assert client.get('/usuarios/me/dados').status_code == 401


def test_anonimizar_conta(client, loja, db):
    from models.usuario_model import Usuarios
    from services import email_service
    from tests.fabrica import SENHA, dados_usuario
    eu = db.get(Usuarios, loja.func.id)
    cpf, telefone, email = eu.cpf, eu.telefone, eu.email
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)])

    r = client.post('/usuarios/me/anonimizacao', headers=loja.func.headers, json={'senha': SENHA})

    assert r.status_code == 200
    db.expire_all()
    eu = db.get(Usuarios, loja.func.id)
    assert (eu.nome, eu.sobrenome, eu.cpf, eu.telefone, eu.status, eu.empresa_id, eu.cargo) == \
        ('Usuário', 'anonimizado', None, None, False, None, None)
    assert eu.email.endswith('@anonimizado.invalid')
    # Acesso encerrado: token atual, refresh e login deixam de funcionar.
    assert client.get('/usuarios/me', headers=loja.func.headers).status_code == 401
    assert renovar(client, loja.func.tokens['refresh_token']).status_code == 401
    assert login(client, email).status_code == 401
    # O histórico fica, sem identificar a pessoa.
    vendas = client.get('/vendas', headers=loja.dono.headers).json()
    assert [v['usuario_id'] for v in vendas] == [loja.func.id]
    # Último aviso para o endereço antigo.
    assert [(e['para'], e['assunto']) for e in email_service.caixa_de_saida] == [(email, 'Sua conta foi anonimizada')]
    # CPF e telefone ficam livres para um novo cadastro da mesma pessoa.
    assert client.post('/usuarios', json=dados_usuario(cpf=cpf, telefone=telefone, email=email)).status_code == 201


def test_anonimizar_exige_senha_e_bloqueia_dono(client, loja):
    from tests.fabrica import SENHA
    assert client.post('/usuarios/me/anonimizacao', headers=loja.func.headers, json={'senha': 'errada'}).status_code == 401
    assert client.get('/usuarios/me', headers=loja.func.headers).status_code == 200  # nada mudou
    r = client.post('/usuarios/me/anonimizacao', headers=loja.dono.headers, json={'senha': SENHA})
    assert r.status_code == 409


def test_anonimizar_conta_sem_empresa(client):
    from tests.fabrica import SENHA
    conta = nova_conta(client)
    assert client.post('/usuarios/me/anonimizacao', headers=conta.headers, json={'senha': SENHA}).status_code == 200
