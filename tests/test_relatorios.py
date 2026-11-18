from io import BytesIO
import pandas as pd
from tests.fabrica import criar_venda, novo_produto


def _cenario(client, loja):
    """2 vendas concluídas + 1 cancelada."""
    h = loja.func.headers
    barato = novo_produto(client, loja.dono.headers, nome='Barato', preco_venda='10.00')
    criar_venda(client, h, [(loja.produto['id'], 2)], cliente_id=loja.cliente['id'], desconto='1.00')  # 51 - 1 = 50
    criar_venda(client, h, [(barato['id'], 3)])                                                         # 30
    vid = criar_venda(client, h, [(barato['id'], 5)]).json()['id']                                      # cancelada
    client.post(f'/vendas/{vid}/cancelar', headers=h, json={'motivo_cancelamento': 'Teste'})
    return barato


def test_resumo(client, loja):
    _cenario(client, loja)
    r = client.get('/relatorios/vendas', headers=loja.dono.headers)
    assert r.status_code == 200
    assert r.json()['resumo'] == {
        'total_vendas': 3,
        'total_vendas_canceladas': 1,
        'taxa_cancelamento': round(1 / 3, 4),
        'total_clientes': 1,
        'ticket_medio': 40.0,          # (50 + 30) / 2 concluídas
        'faturamento_total': 80.0,     # valor_final, sem a cancelada
    }


def test_rankings(client, loja):
    barato = _cenario(client, loja)
    r = client.get('/relatorios/vendas', headers=loja.dono.headers).json()
    assert r['produtos_mais_vendidos'] == [{'produto': 'Barato', 'quantidade': 3},
                                           {'produto': loja.produto['nome'], 'quantidade': 2}]
    assert r['produtos_maior_faturamento'][0] == {'produto': loja.produto['nome'], 'valor_total': 51.0}
    assert r['funcionarios_mais_vendas'] == [{'nome': client.get('/usuarios/me', headers=loja.func.headers).json()['nome'],
                                              'quantidade': 2}]
    assert r['clientes_maior_faturamento'][0]['valor_total'] == 50.0
    assert barato  # usado no cenário


def test_filtro_de_data(client, loja):
    _cenario(client, loja)
    h = loja.dono.headers
    assert client.get('/relatorios/vendas?periodo=mes', headers=h).json()['resumo']['total_vendas'] == 3
    futuro = client.get('/relatorios/vendas?data_inicial=2999-01-01', headers=h).json()
    assert futuro['resumo']['total_vendas'] == 0 and futuro['resumo']['faturamento_total'] == 0


def test_so_dono_acessa(client, loja):
    assert client.get('/relatorios/vendas', headers=loja.func.headers).status_code == 403
    assert client.get('/relatorios/vendas/exportar', headers=loja.func.headers).status_code == 403


def test_exportar_excel_em_memoria(client, loja):
    _cenario(client, loja)
    r = client.get('/relatorios/vendas/exportar?periodo=ano', headers=loja.dono.headers)
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'no-store'
    assert r.headers['content-disposition'].startswith('attachment; filename="relatorio_vendas_')
    abas = pd.read_excel(BytesIO(r.content), sheet_name=None)
    assert len(abas) == 11
    assert abas['Resumo'].loc[0, 'faturamento_total'] == 80.0


def test_relatorio_vazio(client, loja):
    r = client.get('/relatorios/vendas', headers=loja.dono.headers).json()
    assert r['resumo']['total_vendas'] == 0 and r['resumo']['ticket_medio'] == 0
    assert client.get('/relatorios/vendas/exportar', headers=loja.dono.headers).status_code == 200
