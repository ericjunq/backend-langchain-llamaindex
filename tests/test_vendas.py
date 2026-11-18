from tests.fabrica import criar_venda, estoque, nova_conta, novo_produto, gerar_convite, vincular


def test_venda_calcula_valores_no_servidor_e_baixa_estoque(client, loja):
    pid = loja.produto['id']
    r = criar_venda(client, loja.func.headers, [(pid, 2), (pid, 1)],  # itens repetidos são agrupados
                    cliente_id=loja.cliente['id'], desconto='6.50',
                    valor_total='0.01', valor_final='0.01')  # campos ignorados: o servidor calcula
    assert r.status_code == 201
    venda = r.json()
    assert venda['itens'] == [{'produto_id': pid, 'quantidade': 3, 'preco_unitario': '25.50', 'subtotal': '76.50'}]
    assert (venda['valor_total'], venda['desconto'], venda['valor_final']) == ('76.50', '6.50', '70.00')
    assert venda['usuario_id'] == loja.func.id and venda['empresa_id'] == loja.empresa['id']
    assert estoque(client, loja.dono.headers, pid) == 7


def test_venda_sem_cliente(client, loja):
    r = criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)])
    assert r.status_code == 201 and r.json()['cliente_id'] is None


def test_validacoes_de_venda(client, loja):
    h, pid = loja.func.headers, loja.produto['id']
    assert criar_venda(client, h, [(pid, -5)]).status_code == 422
    assert criar_venda(client, h, [(pid, 0)]).status_code == 422
    assert criar_venda(client, h, []).status_code == 422
    assert criar_venda(client, h, [(pid, 1)], desconto='-1').status_code == 422
    assert criar_venda(client, h, [(pid, 1)], desconto='100.00').status_code == 400
    assert criar_venda(client, h, [(pid, 1)], cliente_id=99999).status_code == 404
    assert criar_venda(client, h, [(99999, 1)]).status_code == 404


def test_estoque_insuficiente_nao_altera_nada(client, loja):
    h = loja.func.headers
    outro = novo_produto(client, loja.dono.headers, quantidade=1)
    r = criar_venda(client, h, [(loja.produto['id'], 2), (outro['id'], 5)])
    assert r.status_code == 409
    # Nenhuma baixa parcial: a transação inteira foi desfeita.
    assert estoque(client, h, loja.produto['id']) == 10
    assert estoque(client, h, outro['id']) == 1
    assert client.get('/vendas', headers=loja.dono.headers).json() == []


def test_cancelar_devolve_estoque(client, loja):
    pid = loja.produto['id']
    vid = criar_venda(client, loja.func.headers, [(pid, 4)]).json()['id']
    assert estoque(client, loja.dono.headers, pid) == 6

    r = client.post(f'/vendas/{vid}/cancelar', headers=loja.func.headers,
                     json={'motivo_cancelamento': 'Cliente desistiu'})
    assert r.status_code == 200
    assert r.json()['status'] == 'cancelada' and r.json()['motivo_cancelamento'] == 'Cliente desistiu'
    assert estoque(client, loja.dono.headers, pid) == 10

    again = client.post(f'/vendas/{vid}/cancelar', headers=loja.dono.headers,
                         json={'motivo_cancelamento': 'De novo'})
    assert again.status_code == 400
    assert estoque(client, loja.dono.headers, pid) == 10  # não devolve duas vezes


def test_cancelar_regras(client, loja):
    corpo = {'motivo_cancelamento': 'Motivo'}
    assert client.post('/vendas/99999/cancelar', headers=loja.dono.headers, json=corpo).status_code == 404

    colega = nova_conta(client)
    vincular(client, colega.headers, gerar_convite(client, loja.dono.headers))
    vid = criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)]).json()['id']
    assert client.post(f'/vendas/{vid}/cancelar', headers=colega.headers, json=corpo).status_code == 403
    assert client.post(f'/vendas/{vid}/cancelar', headers=loja.dono.headers, json=corpo).status_code == 200


def test_funcionario_so_ve_as_proprias_vendas(client, loja):
    pid = loja.produto['id']
    criar_venda(client, loja.func.headers, [(pid, 1)])
    criar_venda(client, loja.dono.headers, [(pid, 1)])

    assert len(client.get('/vendas', headers=loja.dono.headers).json()) == 2
    minhas = client.get('/vendas', headers=loja.func.headers).json()
    assert [v['usuario_id'] for v in minhas] == [loja.func.id]

    assert client.get(f'/vendas?usuario_id={loja.dono.id}', headers=loja.func.headers).status_code == 403
    r = client.get(f'/vendas?usuario_id={loja.func.id}&periodo=ano', headers=loja.dono.headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_listagem_ordenada_e_paginada(client, loja):
    pid = loja.produto['id']
    ids = [criar_venda(client, loja.func.headers, [(pid, 1)]).json()['id'] for _ in range(3)]
    h = loja.dono.headers
    assert [v['id'] for v in client.get('/vendas', headers=h).json()] == ids[::-1]
    assert [v['id'] for v in client.get('/vendas?limite=2&offset=1', headers=h).json()] == ids[::-1][1:]
    for periodo in ('mes', 'semestre', 'ano'):
        assert len(client.get(f'/vendas?periodo={periodo}', headers=h).json()) == 3
    assert client.get('/vendas?periodo=semana', headers=h).status_code == 422


def test_obter_venda_por_id(client, loja, outra_loja):
    vid = criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)]).json()['id']
    assert client.get(f'/vendas/{vid}', headers=loja.func.headers).json()['id'] == vid
    assert client.get(f'/vendas/{vid}', headers=loja.dono.headers).status_code == 200
    assert client.get(f'/vendas/{vid}', headers=outra_loja.dono.headers).status_code == 404
    assert client.get('/vendas/99999', headers=loja.dono.headers).status_code == 404

    colega = nova_conta(client)
    vincular(client, colega.headers, gerar_convite(client, loja.dono.headers))
    assert client.get(f'/vendas/{vid}', headers=colega.headers).status_code == 403


def test_filtros_de_vendas(client, loja):
    h, pid, cid = loja.dono.headers, loja.produto['id'], loja.cliente['id']
    v1 = criar_venda(client, loja.func.headers, [(pid, 1)], cliente_id=cid).json()['id']
    v2 = criar_venda(client, loja.func.headers, [(pid, 1)], forma_pagamento='dinheiro').json()['id']
    client.post(f'/vendas/{v2}/cancelar', headers=h, json={'motivo_cancelamento': 'Teste'})

    ids = lambda q: [v['id'] for v in client.get(f'/vendas?{q}', headers=h).json()]
    assert ids(f'cliente_id={cid}') == [v1]
    assert ids('status=cancelada') == [v2]
    assert ids('status=concluida&forma_pagamento=pix') == [v1]
    assert ids(f'usuario_id={loja.dono.id}') == []
