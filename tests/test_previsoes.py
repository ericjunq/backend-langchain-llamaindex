from datetime import datetime, time, timedelta
from decimal import Decimal
import pytest
from services.previsao_service import hoje_local, _fuso
from tests.fabrica import novo_produto


def _no_passado(dias_atras: int) -> datetime:
    """Meio-dia (horário local) de N dias atrás."""
    return datetime.combine(hoje_local() - timedelta(days=dias_atras), time(12), tzinfo=_fuso())


@pytest.fixture
def semear(db):
    """Grava vendas históricas direto no banco (rápido) e 'envelhece' o produto."""
    from models.produto_model import Produtos
    from models.vendas_model import ItemVendas, Vendas
    from utils.enums import FormaPagamento, StatusVenda

    def _semear(loja, produto_id, vendas, cancelada=False):
        produto = db.get(Produtos, produto_id)
        produto.created_at = _no_passado(120)
        for dias_atras, qtd in vendas:
            total = produto.preco_venda * qtd
            venda = Vendas(
                descricao='hist', usuario_id=loja.func.id, empresa_id=loja.empresa['id'],
                forma_pagamento=FormaPagamento.pix, valor_total=total, desconto=Decimal('0'),
                valor_final=total, created_at=_no_passado(dias_atras),
                status=StatusVenda.cancelada if cancelada else StatusVenda.concluida,
            )
            venda.itens.append(ItemVendas(produto_id=produto_id, quantidade=qtd, preco_unitario=produto.preco_venda,
                                          custo_unitario=produto.preco_compra, subtotal=total))
            db.add(venda)
        db.commit()
    return _semear


def _prever(client, loja, pid, dias=30):
    r = client.get(f'/previsoes/produtos/{pid}?dias={dias}', headers=loja.dono.headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_demanda_constante(client, loja, semear):
    pid = loja.produto['id']  # estoque 10
    semear(loja, pid, [(d, 2) for d in range(1, 91)])  # todos os 90 dias do histórico

    p = _prever(client, loja, pid)

    assert p['demanda_prevista'] == 60.0
    assert p['intervalo_80'] == {'minimo': 60.0, 'maximo': 60.0}  # sem variação, sem incerteza
    assert p['media_diaria_prevista'] == 2.0
    assert p['confianca'] == 'alta' and p['historico_dias'] == 90
    assert p['tendencia_pct'] == 0.0
    assert p['dias_ate_ruptura'] == 4  # 2/dia: hoje 2, +1 4, … +4 = 10
    assert len(p['previsao_diaria']) == 30


def test_sazonalidade_semanal(client, loja, semear):
    pid = loja.produto['id']
    hoje = hoje_local()
    sabados = [d for d in range(1, 85) if (hoje - timedelta(days=d)).weekday() == 5]
    semear(loja, pid, [(d, 7) for d in sabados])

    p = _prever(client, loja, pid, dias=28)

    por_dia = {datetime.fromisoformat(str(x['data'])).weekday(): x['quantidade'] for x in p['previsao_diaria']}
    assert por_dia[5] == pytest.approx(7, rel=0.05)    # sábado concentra a demanda
    assert por_dia[2] == pytest.approx(0, abs=0.01)    # quarta não vende
    assert p['demanda_prevista'] == pytest.approx(28, rel=0.05)  # 4 sábados × 7


def test_tendencia_de_alta(client, loja, semear):
    pid = loja.produto['id']
    semear(loja, pid, [(d, 1) for d in range(29, 57)] + [(d, 3) for d in range(1, 29)])
    p = _prever(client, loja, pid)
    assert p['tendencia_pct'] == 200.0
    assert p['media_diaria_prevista'] > 2  # o recente pesa mais que a média simples (2)


def test_ignora_canceladas_e_hoje(client, loja, semear):
    pid = loja.produto['id']
    semear(loja, pid, [(d, 5) for d in range(1, 30)], cancelada=True)
    semear(loja, pid, [(0, 50)])  # hoje: dia incompleto, fica fora do histórico
    p = _prever(client, loja, pid)
    assert p['demanda_prevista'] == 0.0
    assert p['data_ruptura_estimada'] is None
    assert p['confianca'] == 'baixa'


def test_produto_novo_tem_pouca_confianca(client, loja):
    p = _prever(client, loja, loja.produto['id'])
    assert p['historico_dias'] == 0 and p['confianca'] == 'baixa' and p['demanda_prevista'] == 0.0


def test_reposicao(client, loja, semear):
    d = loja.dono.headers
    pid = loja.produto['id']  # estoque 10, mínimo 2, custo 10,00
    semear(loja, pid, [(x, 2) for x in range(1, 91)])
    sem_giro_ok = novo_produto(client, d, nome='Sem giro', quantidade=50, estoque_min=5)
    abaixo_min = novo_produto(client, d, nome='Abaixo do minimo', quantidade=1, estoque_min=4, preco_compra='3.00')

    r = client.get('/previsoes/reposicao?prazo_entrega=7&dias_cobertura=30', headers=d)
    assert r.status_code == 200
    corpo = r.json()
    itens = {i['produto_id']: i for i in corpo['itens']}

    assert sem_giro_ok['id'] not in itens  # não precisa comprar
    principal = itens[pid]
    assert principal['demanda_prevista'] == 74.0                  # 2/dia × 37 dias
    assert principal['ponto_de_pedido'] == 14.0                   # 2/dia × 7 dias de prazo
    assert principal['quantidade_sugerida'] == 64                 # 74 − 10 em estoque
    assert principal['custo_estimado'] == 640.0
    assert principal['urgencia'] == 'comprar_agora'
    assert itens[abaixo_min['id']]['quantidade_sugerida'] == 3     # só completa o mínimo (sem demanda)
    assert corpo['itens'][0]['produto_id'] == pid                  # ruptura mais próxima primeiro
    assert corpo['resumo'] == {'produtos_analisados': 3, 'comprar_agora': 2, 'custo_total_estimado': 649.0}

    todos = client.get('/previsoes/reposicao?apenas_necessarios=false', headers=d).json()
    assert len(todos['itens']) == 3


def test_permissoes_e_validacoes(client, loja, outra_loja):
    pid = loja.produto['id']
    assert client.get(f'/previsoes/produtos/{pid}', headers=loja.func.headers).status_code == 403
    assert client.get('/previsoes/reposicao', headers=loja.func.headers).status_code == 403
    assert client.get(f'/previsoes/produtos/{pid}', headers=outra_loja.dono.headers).status_code == 404
    assert client.get(f'/previsoes/produtos/{pid}?dias=181', headers=loja.dono.headers).status_code == 422
    assert client.get('/previsoes/reposicao?prazo_entrega=-1', headers=loja.dono.headers).status_code == 422


def test_isolamento_entre_empresas(client, loja, outra_loja, semear):
    semear(loja, loja.produto['id'], [(d, 2) for d in range(1, 31)])
    r = client.get('/previsoes/reposicao?apenas_necessarios=false', headers=outra_loja.dono.headers).json()
    assert [i['produto_id'] for i in r['itens']] == [outra_loja.produto['id']]
    assert r['itens'][0]['demanda_prevista'] == 0.0
