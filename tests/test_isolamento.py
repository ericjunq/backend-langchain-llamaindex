"""Uma empresa nunca pode ver nem alterar dados de outra (multiempresa)."""
from tests.fabrica import criar_venda, estoque


def test_nao_le_dados_de_outra_empresa(client, loja, outra_loja):
    h = outra_loja.dono.headers
    assert client.get(f"/produtos/{loja.produto['id']}", headers=h).status_code == 404
    assert client.get(f"/clientes/{loja.cliente['id']}", headers=h).status_code == 404
    assert client.get(f'/vendas?usuario_id={loja.func.id}', headers=h).status_code == 404
    assert client.get(f'/clientes?usuario_id={loja.func.id}', headers=h).status_code == 404

    assert [p['id'] for p in client.get('/produtos', headers=h).json()] == [outra_loja.produto['id']]
    assert [c['id'] for c in client.get('/clientes', headers=h).json()] == [outra_loja.cliente['id']]
    ids_func = {u['id'] for u in client.get('/empresa/funcionarios', headers=h).json()}
    assert ids_func == {outra_loja.dono.id, outra_loja.func.id}


def test_nao_altera_dados_de_outra_empresa(client, loja, outra_loja):
    h = outra_loja.dono.headers
    pid, cid = loja.produto['id'], loja.cliente['id']
    assert client.patch(f'/produtos/{pid}', headers=h, json={'preco_venda': 1}).status_code == 404
    assert client.post(f'/produtos/{pid}/reposicao', headers=h, json={'quantidade': 5}).status_code == 404
    assert client.delete(f'/produtos/{pid}', headers=h).status_code == 404
    assert client.patch(f'/clientes/{cid}', headers=h, json={'nome': 'Hack'}).status_code == 404
    assert client.delete(f'/clientes/{cid}', headers=h).status_code == 404
    assert client.patch(f'/empresa/funcionarios/{loja.func.id}', headers=h, json={'cargo': 'admin'}).status_code == 404
    assert client.delete(f'/empresa/funcionarios/{loja.func.id}', headers=h).status_code == 404


def test_venda_nao_usa_produto_nem_cliente_de_outra_empresa(client, loja, outra_loja):
    h = outra_loja.func.headers
    assert criar_venda(client, h, [(loja.produto['id'], 1)]).status_code == 404
    assert criar_venda(client, h, [(outra_loja.produto['id'], 1)], cliente_id=loja.cliente['id']).status_code == 404
    assert estoque(client, loja.dono.headers, loja.produto['id']) == 10

    vid = criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)]).json()['id']
    r = client.post(f'/vendas/{vid}/cancelar', headers=outra_loja.dono.headers, json={'motivo_cancelamento': 'Hack'})
    assert r.status_code == 404
    assert client.get('/vendas', headers=outra_loja.dono.headers).json() == []


def test_relatorio_so_da_propria_empresa(client, loja, outra_loja):
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 2)])
    r = client.get('/relatorios/vendas', headers=outra_loja.dono.headers).json()
    assert r['resumo']['total_vendas'] == 0 and r['produtos_mais_vendidos'] == []


def test_usuario_sem_empresa_nao_acessa_nada(client, loja):
    from tests.fabrica import nova_conta
    h = nova_conta(client).headers
    for url in ('/produtos', '/clientes', '/vendas',
                '/empresa/funcionarios', '/relatorios/vendas'):
        assert client.get(url, headers=h).status_code == 403, url
