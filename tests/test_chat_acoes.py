"""Ações de escrita pelo chat: o modelo só PREPARA; quem executa é o usuário, confirmando."""
from datetime import datetime, timedelta, timezone
from langchain_core.messages import AIMessage
from main import limpar_dados_expirados
from tests.fabrica import estoque, gerar_convite, nova_conta, vincular
from tests.modelo_falso import chamar


def _preparar_venda(client, conta, modelo, produto, quantidade=3, **extra):
    m = modelo(chamar('registrar_venda', itens=[{'produto': produto, 'quantidade': quantidade}],
                      forma_pagamento='pix', **extra),
               AIMessage('Preparei a venda. Confirme no botão.'))
    r = client.post('/chat', headers=conta.headers, json={'mensagem': 'vende 3 pra maria no pix'})
    assert r.status_code == 200, r.text
    return r.json(), m


def test_venda_so_acontece_depois_de_confirmar(client, loja, modelo):
    pid = loja.produto['id']
    corpo, m = _preparar_venda(client, loja.func, modelo, loja.produto['nome'], cliente=loja.cliente['nome'], desconto=1.5)

    [acao] = corpo['acoes_pendentes']
    assert acao['tipo'] == 'registrar_venda'
    assert acao['resumo'].startswith(f"Venda: 3× {loja.produto['nome']} (R$ 76,50) · pix · cliente ")
    assert acao['resumo'].endswith('desconto R$ 1,50 · total R$ 75,00')
    assert 'NÃO executado' in m.saidas_ferramentas()[0]['situacao']
    assert estoque(client, loja.dono.headers, pid) == 10  # nada mudou ainda
    assert client.get('/vendas', headers=loja.dono.headers).json() == []

    r = client.post(f"/chat/acoes/{acao['id']}/confirmar", headers=loja.func.headers)
    assert r.status_code == 200
    venda = r.json()['resultado']
    assert (venda['valor_final'], venda['usuario_id'], venda['cliente_id']) == ('75.00', loja.func.id, loja.cliente['id'])
    assert estoque(client, loja.dono.headers, pid) == 7

    # Não executa duas vezes.
    assert client.post(f"/chat/acoes/{acao['id']}/confirmar", headers=loja.func.headers).status_code == 404
    assert len(client.get('/vendas', headers=loja.dono.headers).json()) == 1


def test_cancelar_acao(client, loja, modelo):
    corpo, _ = _preparar_venda(client, loja.func, modelo, loja.produto['nome'])
    acao_id = corpo['acoes_pendentes'][0]['id']
    assert client.delete(f'/chat/acoes/{acao_id}', headers=loja.func.headers).status_code == 204
    assert client.post(f'/chat/acoes/{acao_id}/confirmar', headers=loja.func.headers).status_code == 404
    assert estoque(client, loja.dono.headers, loja.produto['id']) == 10


def test_so_quem_pediu_confirma(client, loja, outra_loja, modelo):
    corpo, _ = _preparar_venda(client, loja.func, modelo, loja.produto['nome'])
    acao_id = corpo['acoes_pendentes'][0]['id']
    for intruso in (loja.dono, outra_loja.dono):  # nem o dono da mesma empresa
        assert client.post(f'/chat/acoes/{acao_id}/confirmar', headers=intruso.headers).status_code == 404
        assert client.delete(f'/chat/acoes/{acao_id}', headers=intruso.headers).status_code == 404


def test_acao_expirada(client, loja, modelo, db):
    from models.acao_pendente import AcaoPendente
    corpo, _ = _preparar_venda(client, loja.func, modelo, loja.produto['nome'])
    acao_id = corpo['acoes_pendentes'][0]['id']
    db.get(AcaoPendente, acao_id).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    assert client.post(f'/chat/acoes/{acao_id}/confirmar', headers=loja.func.headers).status_code == 410
    db.expire_all()
    assert db.get(AcaoPendente, acao_id) is None  # expirada é apagada


def test_estoque_mudou_entre_preparar_e_confirmar(client, loja, modelo, db):
    from models.acao_pendente import AcaoPendente
    pid = loja.produto['id']
    corpo, _ = _preparar_venda(client, loja.func, modelo, loja.produto['nome'], quantidade=8)
    acao_id = corpo['acoes_pendentes'][0]['id']
    from tests.fabrica import criar_venda
    assert criar_venda(client, loja.dono.headers, [(pid, 5)]).status_code == 201  # sobram 5

    r = client.post(f'/chat/acoes/{acao_id}/confirmar', headers=loja.func.headers)
    assert r.status_code == 409
    db.expire_all()
    assert db.get(AcaoPendente, acao_id) is not None  # falhou: a ação continua (dá para cancelar)
    assert estoque(client, loja.dono.headers, pid) == 5


def test_venda_invalida_nao_cria_acao(client, loja, outra_loja, modelo):
    m = modelo(
        chamar('registrar_venda', itens=[{'produto': loja.produto['nome'], 'quantidade': 99}], forma_pagamento='pix'),
        chamar('registrar_venda', itens=[{'produto': outra_loja.produto['nome'], 'quantidade': 1}], forma_pagamento='pix'),
        chamar('registrar_venda', itens=[{'produto': loja.produto['nome'], 'quantidade': 0}], forma_pagamento='pix'),
        chamar('registrar_venda', itens=[{'produto': loja.produto['nome'], 'quantidade': 1}], forma_pagamento='fiado'),
        AIMessage('Não deu.'))
    r = client.post('/chat', headers=loja.func.headers, json={'mensagem': 'vende'})
    assert r.json()['acoes_pendentes'] == []
    saidas = m.saidas_ferramentas()
    assert saidas[0] == {'erro': f"Estoque insuficiente de {loja.produto['nome']}: há 10"}
    assert saidas[1] == {'erro': f'Produto "{outra_loja.produto["nome"]}" não encontrado'}
    assert all('erro' in s for s in saidas[2:])


def test_repor_estoque_pelo_chat(client, loja, modelo):
    pid = loja.produto['id']
    modelo(chamar('repor_estoque', produto=loja.produto['nome'], quantidade=20), AIMessage('Confirme a entrada.'))
    r = client.post('/chat', headers=loja.dono.headers, json={'mensagem': 'chegaram 20'})
    [acao] = r.json()['acoes_pendentes']
    assert acao['resumo'] == f"Repor estoque: +20 × {loja.produto['nome']} (estoque 10 → 30)"
    assert estoque(client, loja.dono.headers, pid) == 10

    r = client.post(f"/chat/acoes/{acao['id']}/confirmar", headers=loja.dono.headers)
    assert r.status_code == 200 and r.json()['resultado']['quantidade'] == 30


def test_funcionario_nao_prepara_reposicao(client, loja, modelo):
    m = modelo(chamar('repor_estoque', produto=loja.produto['nome'], quantidade=5), AIMessage('Sem permissão.'))
    r = client.post('/chat', headers=loja.func.headers, json={'mensagem': 'repõe 5'})
    assert r.json()['acoes_pendentes'] == []
    assert m.saidas_ferramentas() == [{'erro': 'Você não tem permissão para repor estoque'}]


def test_perdeu_permissao_antes_de_confirmar(client, loja, modelo):
    admin = nova_conta(client)
    vincular(client, admin.headers, gerar_convite(client, loja.dono.headers))
    client.patch(f'/empresa/funcionarios/{admin.id}', headers=loja.dono.headers, json={'cargo': 'admin'})
    modelo(chamar('repor_estoque', produto=loja.produto['codigo_produto'], quantidade=5), AIMessage('ok'))  # por código
    acao_id = client.post('/chat', headers=admin.headers, json={'mensagem': 'repõe'}).json()['acoes_pendentes'][0]['id']

    client.patch(f'/empresa/funcionarios/{admin.id}', headers=loja.dono.headers, json={'cargo': 'funcionario'})
    assert client.post(f'/chat/acoes/{acao_id}/confirmar', headers=admin.headers).status_code == 403


def test_retencao_apaga_acoes_vencidas(client, loja, modelo, db):
    from models.acao_pendente import AcaoPendente
    _preparar_venda(client, loja.func, modelo, loja.produto['nome'])
    db.query(AcaoPendente).update({'expires_at': datetime.now(timezone.utc) - timedelta(minutes=1)})
    db.commit()
    limpar_dados_expirados()
    assert db.query(AcaoPendente).count() == 0


def test_produto_por_nome_ambiguo_ou_aproximado(client, loja, modelo):
    from tests.fabrica import novo_produto
    novo_produto(client, loja.dono.headers, nome='Café Especial')
    novo_produto(client, loja.dono.headers, nome='Café Comum')
    m = modelo(
        chamar('repor_estoque', produto='cafe', quantidade=1),          # ambíguo → pergunta
        chamar('repor_estoque', produto='CAFE COMUM', quantidade=1),    # exato (sem acento/caixa) → resolve
        AIMessage('ok'))
    r = client.post('/chat', headers=loja.dono.headers, json={'mensagem': 'repõe café'})
    ambiguo, resolvido = m.saidas_ferramentas()
    assert 'Mais de um produto' in ambiguo['erro'] and 'Café Especial' in ambiguo['erro'] and 'Café Comum' in ambiguo['erro']
    assert 'Café Comum' in resolvido['resumo']
    assert len(r.json()['acoes_pendentes']) == 1
