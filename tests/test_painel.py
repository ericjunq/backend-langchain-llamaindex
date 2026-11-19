from datetime import datetime, time, timedelta
from services.painel_service import _mes_anterior
from services.previsao_service import _fuso, hoje_local
from tests.fabrica import criar_venda, novo_produto


def _painel(client, conta):
    r = client.get('/painel', headers=conta.headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_funcionario_ve_so_as_proprias_vendas(client, loja):
    pid = loja.produto['id']
    criar_venda(client, loja.func.headers, [(pid, 2)], cliente_id=loja.cliente['id'])  # 51,00
    criar_venda(client, loja.dono.headers, [(pid, 1)])                                   # do dono: não conta
    cancelada = criar_venda(client, loja.func.headers, [(pid, 1)]).json()['id']
    client.post(f'/vendas/{cancelada}/cancelar', headers=loja.func.headers, json={'motivo_cancelamento': 'Teste'})

    p = _painel(client, loja.func)

    assert p['minhas_vendas'] == {'hoje': {'quantidade': 1, 'total': 51.0}, 'mes': {'quantidade': 1, 'total': 51.0}}
    assert [v['status'] for v in p['minhas_ultimas_vendas']] == ['cancelada', 'concluida']  # inclui canceladas
    assert p['empresa'] is None  # funcionário não vê a visão da empresa


def test_cliente_aparece_abreviado(client, loja, db):
    from models.cliente_model import Clientes
    db.get(Clientes, loja.cliente['id']).nome = 'Maria Souza Lima'
    db.commit()
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)], cliente_id=loja.cliente['id'])
    p = _painel(client, loja.func)
    assert p['minhas_ultimas_vendas'][0]['cliente'] == 'Maria S.'
    assert 'Souza Lima' not in str(p)


def test_gestor_ve_a_empresa(client, loja):
    d = loja.dono.headers
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 2)])  # 51,00 hoje
    novo_produto(client, d, nome='Quase acabando', quantidade=1, estoque_min=5)

    empresa = _painel(client, loja.dono)['empresa']

    assert empresa['faturamento_mes'] == 51.0 and empresa['vendas_mes'] == 1
    assert len(empresa['vendas_por_dia']) == 30
    assert empresa['vendas_por_dia'][-1] == {'data': hoje_local().isoformat(), 'quantidade': 1, 'total': 51.0}
    assert empresa['estoque_abaixo_minimo']['total'] == 1
    assert empresa['estoque_abaixo_minimo']['itens'][0]['produto'] == 'Quase acabando'
    assert set(empresa['reposicao']['por_necessidade']) == {'comprar_agora', 'em_breve', 'ok'}
    assert 'gasto_estimado_reposicao' in empresa['reposicao']


def test_comparacao_com_o_mesmo_periodo_do_mes_anterior(client, loja, db):
    from models.vendas_model import Vendas
    hoje = hoje_local()
    inicio_anterior, mesmo_dia_anterior = _mes_anterior(hoje)
    dentro = criar_venda(client, loja.dono.headers, [(loja.produto['id'], 4)]).json()['id']   # 102,00
    fora = criar_venda(client, loja.dono.headers, [(loja.produto['id'], 2)]).json()['id']     # 51,00
    criar_venda(client, loja.dono.headers, [(loja.produto['id'], 2)])                           # hoje: 51,00
    db.get(Vendas, dentro).created_at = datetime.combine(inicio_anterior, time(12), tzinfo=_fuso())
    # Um dia depois do "mesmo dia" do mês anterior: fica fora da comparação (se ainda for mês anterior).
    depois = mesmo_dia_anterior + timedelta(days=1)
    db.get(Vendas, fora).created_at = datetime.combine(
        depois if depois.month == inicio_anterior.month else inicio_anterior - timedelta(days=1), time(12), tzinfo=_fuso())
    db.commit()

    empresa = _painel(client, loja.dono)['empresa']
    assert empresa['faturamento_mes'] == 51.0
    assert empresa['faturamento_mesmo_periodo_mes_anterior'] == 102.0
    assert empresa['variacao_pct'] == -50.0


def test_mes_anterior_mais_curto():
    from datetime import date
    assert _mes_anterior(date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert _mes_anterior(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 15))


def test_isolamento_e_sem_empresa(client, loja, outra_loja):
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 2)])
    outra = _painel(client, outra_loja.dono)
    assert outra['empresa']['faturamento_mes'] == 0 and outra['minhas_ultimas_vendas'] == []
    from tests.fabrica import nova_conta
    assert client.get('/painel', headers=nova_conta(client).headers).status_code == 403
