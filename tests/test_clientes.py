from tests.fabrica import criar_venda, gerar_cpf, nova_conta, novo_cliente, gerar_convite, vincular


def test_resposta_nao_expoe_dados_pessoais(client, loja):
    assert set(loja.cliente) == {'id', 'nome', 'created_at', 'updated_at'}


def test_cpf_ou_email_duplicado_na_mesma_empresa(client, loja, db):
    from models.cliente_model import Clientes
    existente = db.get(Clientes, loja.cliente['id'])
    r = client.post('/clientes', headers=loja.dono.headers, json={
        'nome': 'Outro', 'email': 'novo@teste.com', 'cpf': existente.cpf, 'telefone': '11977776666'})
    assert r.status_code == 409


def test_mesmo_cpf_em_empresas_diferentes(client, loja, outra_loja):
    cpf = gerar_cpf()
    novo_cliente(client, loja.dono.headers, cpf=cpf)
    novo_cliente(client, outra_loja.dono.headers, cpf=cpf)


def test_funcionario_so_edita_os_proprios_clientes(client, loja):
    colega = nova_conta(client)
    assert vincular(client, colega.headers, gerar_convite(client, loja.dono.headers)).status_code == 200

    url = f"/clientes/{loja.cliente['id']}"
    assert client.patch(url, headers=colega.headers, json={'nome': 'Novo'}).status_code == 403
    assert client.patch(url, headers=loja.func.headers, json={'nome': 'Novo Nome'}).json()['nome'] == 'Novo Nome'
    assert client.patch(url, headers=loja.dono.headers, json={'nome': 'Pelo Dono'}).status_code == 200


def test_funcionario_nao_deleta_cliente(client, loja):
    assert client.delete(f"/clientes/{loja.cliente['id']}", headers=loja.func.headers).status_code == 403


def test_deletar_sem_vendas_apaga(client, loja, db):
    from models.cliente_model import Clientes
    cid = loja.cliente['id']
    assert client.delete(f'/clientes/{cid}', headers=loja.dono.headers).status_code == 200
    assert db.get(Clientes, cid) is None


def test_deletar_com_vendas_anonimiza(client, loja, db):
    from models.cliente_model import Clientes
    cid = loja.cliente['id']
    assert criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)], cliente_id=cid).status_code == 201

    r = client.delete(f'/clientes/{cid}', headers=loja.dono.headers)

    assert r.status_code == 200 and 'anonimizados' in r.json()['message']
    cliente = db.get(Clientes, cid)
    assert (cliente.nome, cliente.email, cliente.cpf, cliente.telefone, cliente.status) == \
        ('Cliente anonimizado', None, None, None, False)
    assert client.get(f'/clientes/{cid}', headers=loja.dono.headers).status_code == 404
    # A venda continua existindo (histórico financeiro).
    assert len(client.get('/vendas', headers=loja.dono.headers).json()) == 1


def test_buscar_e_listar(client, loja):
    h = loja.dono.headers
    novo_cliente(client, h, nome='Maria Souza')
    busca = client.post('/clientes/busca', headers=h, json={'nome': 'maria'})
    assert [c['nome'] for c in busca.json()] == ['Maria Souza']
    assert client.post('/clientes/busca', headers=h, json={'cpf': '123'}).status_code == 422
    assert len(client.get('/clientes?periodo=semestre', headers=h).json()) == 2
    assert len(client.get('/clientes?limite=1', headers=h).json()) == 1


def test_clientes_por_funcionario(client, loja):
    url = f'/clientes?usuario_id={loja.func.id}'
    assert [c['id'] for c in client.get(url, headers=loja.dono.headers).json()] == [loja.cliente['id']]
    assert client.get(url, headers=loja.func.headers).status_code == 200
    outro = f'/clientes?usuario_id={loja.dono.id}'
    assert client.get(outro, headers=loja.func.headers).status_code == 403
