from io import BytesIO
import pandas as pd
from tests.fabrica import criar_venda, novo_produto


def _cenario(client, loja):
    """
    loja.produto: custo 10,00 · venda 25,50 · estoque 10 → vende 4 → sobra 6
    caro:         custo 50,00 · venda 60,00 · estoque 3, mín. 5 → vende 1 → sobra 2 (abaixo do mínimo)
    parado:       custo 8,00 · estoque 7 → sem venda
    zerado:       estoque 0 → sem venda, sem estoque
    + uma venda cancelada do 'parado' (não pode contar)
    """
    d, f = loja.dono.headers, loja.func.headers
    caro = novo_produto(client, d, nome='Caro', preco_compra='50.00', preco_venda='60.00', quantidade=3, estoque_min=5)
    parado = novo_produto(client, d, nome='Parado', preco_compra='8.00', preco_venda='12.00', quantidade=7, estoque_min=1)
    novo_produto(client, d, nome='Zerado', quantidade=0, estoque_min=0)

    criar_venda(client, f, [(loja.produto['id'], 3), (caro['id'], 1)])
    criar_venda(client, f, [(loja.produto['id'], 1)])
    cancelada = criar_venda(client, f, [(parado['id'], 2)]).json()['id']
    client.post(f'/vendas/{cancelada}/cancelar', headers=f, json={'motivo_cancelamento': 'Teste'})
    return caro, parado


def test_resumo_de_estoque_e_margem(client, loja):
    _cenario(client, loja)
    r = client.get('/relatorios/produtos', headers=loja.dono.headers)
    assert r.status_code == 200
    resumo = r.json()['resumo']
    assert resumo['total_produtos'] == 4
    assert resumo['abaixo_estoque_min'] == 2          # Caro (2 ≤ 5) e Zerado (0 ≤ 0)
    assert resumo['sem_estoque'] == 1
    assert resumo['valor_estoque_custo'] == 6 * 10 + 2 * 50 + 7 * 8  # 216
    assert resumo['unidades_vendidas'] == 5
    assert resumo['faturamento_bruto'] == 4 * 25.5 + 60            # 162
    assert resumo['custo_vendido'] == 4 * 10 + 50                  # 90
    assert resumo['margem'] == 72.0
    assert resumo['margem_pct'] == round(72 / 162 * 100, 2)
    assert resumo['produtos_sem_venda'] == 2                       # Parado (venda cancelada) e Zerado


def test_rankings_e_reposicao(client, loja):
    _cenario(client, loja)
    r = client.get('/relatorios/produtos', headers=loja.dono.headers).json()
    nome = loja.produto['nome']

    assert r['mais_vendidos'][0] == {'produto': nome, 'vendido': 4, 'faturamento': 102.0}
    assert r['maior_margem'][0] == {'produto': nome, 'margem': 62.0, 'margem_pct': round(62 / 102 * 100, 2)}
    assert r['menor_margem'][0]['produto'] == 'Caro'
    assert r['sem_venda'][0] == {'produto': 'Parado', 'estoque': 7, 'valor_parado': 56.0}
    assert [p['produto'] for p in r['reposicao']] == ['Caro', 'Zerado']  # quem acaba antes vem primeiro
    caro = r['reposicao'][0]
    assert caro['media_diaria'] > 0 and caro['dias_estoque'] is not None
    assert r['reposicao'][1]['dias_estoque'] is None  # sem venda: sem previsão


def test_margem_usa_custo_da_epoca_da_venda(client, loja):
    pid = loja.produto['id']
    criar_venda(client, loja.func.headers, [(pid, 1)])
    client.patch(f'/produtos/{pid}', headers=loja.dono.headers, json={'preco_compra': '20.00'})
    r = client.get('/relatorios/produtos', headers=loja.dono.headers).json()
    assert r['resumo']['custo_vendido'] == 10.0  # custo de quando vendeu, não o novo


def test_produto_desativado_que_vendeu_continua_no_faturamento(client, loja):
    pid = loja.produto['id']
    criar_venda(client, loja.func.headers, [(pid, 2)])
    client.delete(f'/produtos/{pid}', headers=loja.dono.headers)  # tem venda → desativa
    resumo = client.get('/relatorios/produtos', headers=loja.dono.headers).json()['resumo']
    assert resumo['total_produtos'] == 0
    assert resumo['faturamento_bruto'] == 51.0


def test_filtro_de_data(client, loja):
    _cenario(client, loja)
    r = client.get('/relatorios/produtos?data_inicial=2999-01-01', headers=loja.dono.headers).json()
    assert r['resumo']['unidades_vendidas'] == 0 and r['mais_vendidos'] == []
    assert r['resumo']['total_produtos'] == 4  # o estoque atual não depende do período


def test_permissoes(client, loja):
    from tests.fabrica import gerar_convite, nova_conta, vincular
    assert client.get('/relatorios/produtos', headers=loja.func.headers).status_code == 403
    admin = nova_conta(client)
    vincular(client, admin.headers, gerar_convite(client, loja.dono.headers))
    client.patch(f'/empresa/funcionarios/{admin.id}', headers=loja.dono.headers, json={'cargo': 'admin'})
    assert client.get('/relatorios/produtos', headers=admin.headers).status_code == 200
    assert client.get('/relatorios/vendas', headers=admin.headers).status_code == 403  # vendas segue só do dono


def test_empresa_sem_produtos(client, loja):
    client.delete(f"/produtos/{loja.produto['id']}", headers=loja.dono.headers)
    r = client.get('/relatorios/produtos', headers=loja.dono.headers)
    assert r.status_code == 200 and r.json()['resumo']['total_produtos'] == 0
    assert client.get('/relatorios/produtos/exportar', headers=loja.dono.headers).status_code == 200


def test_exportar_excel(client, loja):
    _cenario(client, loja)
    r = client.get('/relatorios/produtos/exportar', headers=loja.dono.headers)
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    assert 'relatorio_produtos_' in r.headers['content-disposition']
    abas = pd.read_excel(BytesIO(r.content), sheet_name=None)
    assert list(abas) == ['Resumo', 'Produtos', 'Reposição', 'Sem Venda', 'Mais Vendidos', 'Maior Margem', 'Menor Margem']
    assert len(abas['Produtos']) == 4
