"""LGPD — direitos do titular."""
from tests.fabrica import criar_venda, login, nova_conta


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
