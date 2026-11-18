from tests.fabrica import criar_venda, estoque, novo_produto


def test_cadastro_gera_codigo_e_guarda_preco_exato(client, loja):
    p = loja.produto
    assert p['codigo_produto'].startswith('PROD-') and len(p['codigo_produto']) == 13
    assert p['preco_venda'] == '25.50'


def test_nome_duplicado_ignora_acento_e_caixa(client, loja):
    novo_produto(client, loja.dono.headers, nome='Café Especial')
    r = client.post('/produtos/cadastrar_produto', headers=loja.dono.headers, json={
        'nome': 'CAFE  especial', 'descricao': 'x', 'quantidade': 1,
        'preco_compra': 1, 'preco_venda': 2, 'estoque_min': 0})
    assert r.status_code == 409


def test_validacoes_de_cadastro(client, loja):
    base = {'nome': 'X', 'descricao': 'x', 'quantidade': 1, 'preco_compra': 1, 'preco_venda': 2, 'estoque_min': 0}
    for campo, valor in [('preco_venda', -1), ('quantidade', -1), ('nome', 'x' * 31)]:
        r = client.post('/produtos/cadastrar_produto', headers=loja.dono.headers, json={**base, campo: valor})
        assert r.status_code == 422, campo


def test_funcionario_nao_gerencia_produtos(client, loja):
    h, pid = loja.func.headers, loja.produto['id']
    assert client.post('/produtos/cadastrar_produto', headers=h, json={
        'nome': 'X', 'descricao': 'x', 'quantidade': 1, 'preco_compra': 1, 'preco_venda': 2, 'estoque_min': 0}).status_code == 403
    assert client.patch(f'/produtos/editar_produto/{pid}', headers=h, json={'preco_venda': 1}).status_code == 403
    assert client.patch(f'/produtos/repor_estoque/{pid}', headers=h, json={'quantidade': 5}).status_code == 403
    assert client.delete(f'/produtos/deletar_produto/{pid}', headers=h).status_code == 403


def test_repor_estoque(client, loja):
    pid = loja.produto['id']
    assert client.patch(f'/produtos/repor_estoque/{pid}', headers=loja.dono.headers, json={'quantidade': 0}).status_code == 422
    r = client.patch(f'/produtos/repor_estoque/{pid}', headers=loja.dono.headers, json={'quantidade': 5})
    assert r.status_code == 200 and r.json()['quantidade'] == 15


def test_editar_produto(client, loja):
    r = client.patch(f"/produtos/editar_produto/{loja.produto['id']}", headers=loja.dono.headers,
                     json={'preco_venda': '30.00', 'descricao': None})
    assert r.status_code == 200
    assert r.json()['preco_venda'] == '30.00'
    assert r.json()['descricao'] == loja.produto['descricao']  # None não apaga o campo


def test_buscar_produto(client, loja):
    h = loja.dono.headers
    novo_produto(client, h, nome='Pão de Açúcar', quantidade=1, estoque_min=5)
    assert [p['nome'] for p in client.get('/produtos/buscar_produto?nome=acucar', headers=h).json()] == ['Pão de Açúcar']
    abaixo = client.get('/produtos/buscar_produto?abaixo_estoque_min=true', headers=h).json()
    assert [p['nome'] for p in abaixo] == ['Pão de Açúcar']
    codigo = loja.produto['codigo_produto'].lower()
    assert len(client.get(f'/produtos/buscar_produto?codigo_produto={codigo}', headers=h).json()) == 1


def test_deletar_sem_vendas_apaga(client, loja):
    pid = loja.produto['id']
    r = client.delete(f'/produtos/deletar_produto/{pid}', headers=loja.dono.headers)
    assert r.status_code == 200 and 'deletado' in r.json()['message']
    assert client.get(f'/produtos/buscar_produto_por_id/{pid}', headers=loja.dono.headers).status_code == 404


def test_deletar_com_vendas_desativa(client, loja, db):
    from models.produto_model import Produtos
    pid = loja.produto['id']
    assert criar_venda(client, loja.func.headers, [(pid, 1)]).status_code == 201

    r = client.delete(f'/produtos/deletar_produto/{pid}', headers=loja.dono.headers)
    assert r.status_code == 200 and 'desativado' in r.json()['message']
    assert db.get(Produtos, pid).ativo is False  # histórico preservado
    assert client.get('/produtos/listar_produtos', headers=loja.dono.headers).json() == []
    assert criar_venda(client, loja.func.headers, [(pid, 1)]).status_code == 404


def test_listar_produtos_com_filtros_de_data(client, loja):
    h = loja.dono.headers
    assert len(client.get('/produtos/listar_produtos?periodo=mes', headers=h).json()) == 1
    assert client.get('/produtos/listar_produtos?data_inicial=2999-01-01', headers=h).json() == []
    assert client.get('/produtos/listar_produtos?data_inicial=2025-02-01&data_final=2025-01-01', headers=h).status_code == 400
    assert client.get('/produtos/listar_produtos?periodo=ano&data_final=2025-01-01', headers=h).status_code == 400
    assert estoque(client, h, loja.produto['id']) == 10
