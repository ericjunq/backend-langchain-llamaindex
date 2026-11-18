"""Previsão de demanda e sugestão de reposição (v1, estatística, sem LLM).

Método (por produto, vetorizado para todos de uma vez):
  1. Série diária de unidades vendidas (vendas concluídas) nos últimos HISTORICO_DIAS dias,
     no fuso da empresa, terminando ONTEM (o dia de hoje ainda está incompleto).
  2. Nível = média móvel de 7 dias (remove o ciclo semanal) suavizada por média
     exponencial (meia-vida de MEIA_VIDA_DIAS: o passado recente pesa mais).
  3. Sazonalidade semanal = média do dia da semana ÷ média geral (só com ≥ 4 semanas de histórico).
  4. Previsão do dia = nível × fator do dia da semana.
  5. Incerteza = desvio-padrão diário; intervalo de ~80% e estoque de segurança de ~95%.

Desempenho: 2 consultas no total (produtos + série agregada por produto/dia), qualquer que
seja o número de produtos. O filtro de data usa o índice (empresa_id, created_at).
LGPD: usa só quantidades e datas; nenhum dado pessoal.
"""
import math
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from models.produto_model import Produtos
from models.usuario_model import Usuarios
from models.vendas_model import ItemVendas, Vendas
from security.permissoes import GESTORES, exigir_cargo
from security.settings import settings
from utils.enums import StatusVenda

METODO = 'media_movel_exponencial_sazonal_v1'
HISTORICO_DIAS = 90
MEIA_VIDA_DIAS = 14
MIN_DIAS_SAZONALIDADE = 28
Z_INTERVALO_80 = 1.28
Z_SEGURANCA_95 = 1.65


def _fuso() -> ZoneInfo:
    return ZoneInfo(settings.fuso_horario)


def hoje_local() -> date:
    return datetime.now(_fuso()).date()


def _confianca(dias_historico: int, unidades: float) -> str:
    if dias_historico < 14 or unidades < 5:
        return 'baixa'
    if dias_historico < 56:
        return 'media'
    return 'alta'


def _serie_diaria(db: Session, usuario: Usuarios, produtos: pd.DataFrame, hoje: date) -> pd.DataFrame:
    """Matriz dias × produtos com as unidades vendidas por dia (NaN antes de o produto existir)."""
    inicio = hoje - timedelta(days=HISTORICO_DIAS)
    fim = hoje - timedelta(days=1)
    dias = pd.date_range(inicio, fim, freq='D')
    ids = produtos.index.tolist()

    # Filtro em created_at puro (usa o índice); a conversão para o dia local só no SELECT/GROUP BY.
    inicio_ts = datetime.combine(inicio, time.min, tzinfo=_fuso())
    fim_ts = datetime.combine(hoje, time.min, tzinfo=_fuso())
    dia = cast(func.timezone(settings.fuso_horario, Vendas.created_at), Date).label('dia')

    linhas = (
        db.query(ItemVendas.produto_id, dia, func.sum(ItemVendas.quantidade))
        .join(Vendas, Vendas.id == ItemVendas.venda_id)
        .filter(
            Vendas.empresa_id == usuario.empresa_id,
            Vendas.status != StatusVenda.cancelada,
            Vendas.created_at >= inicio_ts,
            Vendas.created_at < fim_ts,
            ItemVendas.produto_id.in_(ids),
        )
        .group_by(ItemVendas.produto_id, dia)
        .all()
    )

    vendas = pd.DataFrame(linhas, columns=['produto_id', 'dia', 'qtd'])
    if vendas.empty:
        matriz = pd.DataFrame(0.0, index=dias, columns=ids)
    else:
        vendas['dia'] = pd.to_datetime(vendas['dia'])
        vendas['qtd'] = vendas['qtd'].astype(float)
        matriz = (
            vendas.pivot_table(index='dia', columns='produto_id', values='qtd', aggfunc='sum')
            .reindex(index=dias, columns=ids)
            .fillna(0.0)
        )

    # Antes de o produto existir não é "zero venda", é "sem dado": vira NaN.
    criacao = pd.to_datetime(produtos['criado_em_local']).to_numpy()
    antes_de_existir = dias.to_numpy()[:, None] < criacao[None, :]
    return matriz.mask(antes_de_existir)


def _prever(matriz: pd.DataFrame, horizonte: int, hoje: date) -> dict:
    """Aplica o método a todas as colunas (produtos) de uma vez."""
    dias_hist = matriz.notna().sum()
    total_hist = matriz.sum()  # NaN é ignorado

    nivel = (
        matriz.rolling(7, min_periods=1).mean()
        .ewm(halflife=MEIA_VIDA_DIAS, ignore_na=True).mean()
        .iloc[-1]
        .fillna(0.0)
    ) if len(matriz) else pd.Series(0.0, index=matriz.columns)

    media = matriz.mean()
    por_dia_semana = matriz.groupby(matriz.index.dayofweek).mean().reindex(range(7))
    fatores = por_dia_semana.div(media.where(media > 0)).fillna(1.0)
    fatores = fatores.div(fatores.mean())  # média dos 7 fatores = 1 (não altera o nível)
    fatores.loc[:, dias_hist < MIN_DIAS_SAZONALIDADE] = 1.0

    futuro = pd.date_range(hoje, periods=horizonte, freq='D')
    previsao = pd.DataFrame(
        nivel.to_numpy()[None, :] * fatores.loc[futuro.dayofweek].to_numpy(),
        index=futuro, columns=matriz.columns,
    ).clip(lower=0)

    desvio = matriz.std().fillna(0.0)

    tendencia = pd.Series(np.nan, index=matriz.columns)
    if len(matriz) >= 56:
        recente, anterior = matriz.iloc[-28:].mean(), matriz.iloc[-56:-28].mean()
        tendencia = ((recente - anterior) / anterior * 100).where((anterior > 0) & (dias_hist >= 56))

    return {
        'previsao': previsao, 'desvio': desvio, 'dias_hist': dias_hist,
        'total_hist': total_hist, 'tendencia': tendencia,
    }


def _data_ruptura(previsao_produto: pd.Series, estoque: int) -> Optional[date]:
    if estoque <= 0:
        return previsao_produto.index[0].date()
    acumulado = previsao_produto.cumsum()
    atingiu = acumulado[acumulado >= estoque]
    return atingiu.index[0].date() if len(atingiu) else None


def _produtos(db: Session, usuario: Usuarios, produto_id: Optional[int] = None) -> pd.DataFrame:
    dia_criacao = cast(func.timezone(settings.fuso_horario, Produtos.created_at), Date)
    query = db.query(
        Produtos.id, Produtos.nome, Produtos.codigo_produto, Produtos.quantidade,
        Produtos.estoque_min, Produtos.preco_compra, dia_criacao,
    ).filter(Produtos.empresa_id == usuario.empresa_id, Produtos.ativo.is_(True))
    if produto_id is not None:
        query = query.filter(Produtos.id == produto_id)

    df = pd.DataFrame(query.all(), columns=['id', 'produto', 'codigo', 'estoque', 'estoque_min',
                                            'preco_compra', 'criado_em_local'])
    df['preco_compra'] = df['preco_compra'].astype(float)
    return df.set_index('id')


def _arredondar(valor, casas=2):
    return None if valor is None or (isinstance(valor, float) and math.isnan(valor)) else round(float(valor), casas)


def prever_produto(db: Session, usuario: Usuarios, produto_id: int, dias: int) -> dict:
    exigir_cargo(usuario, *GESTORES)
    produtos = _produtos(db, usuario, produto_id)
    if produtos.empty:
        raise HTTPException(status_code=404, detail='Produto não encontrado')

    hoje = hoje_local()
    r = _prever(_serie_diaria(db, usuario, produtos, hoje), dias, hoje)
    p = produtos.iloc[0]
    serie = r['previsao'][produto_id]
    total, desvio = float(serie.sum()), float(r['desvio'][produto_id])
    margem = Z_INTERVALO_80 * desvio * math.sqrt(dias)
    ruptura = _data_ruptura(serie, int(p['estoque']))
    dias_hist = int(r['dias_hist'][produto_id])

    return {
        'produto_id': produto_id,
        'produto': p['produto'],
        'estoque_atual': int(p['estoque']),
        'horizonte_dias': dias,
        'demanda_prevista': _arredondar(total),
        'intervalo_80': {'minimo': _arredondar(max(total - margem, 0)), 'maximo': _arredondar(total + margem)},
        'media_diaria_prevista': _arredondar(total / dias),
        'tendencia_pct': _arredondar(r['tendencia'][produto_id], 1),
        'data_ruptura_estimada': ruptura,
        'dias_ate_ruptura': (ruptura - hoje).days if ruptura else None,
        'historico_dias': dias_hist,
        'confianca': _confianca(dias_hist, float(r['total_hist'][produto_id])),
        'metodo': METODO,
        'previsao_diaria': [{'data': d.date(), 'quantidade': round(float(q), 2)} for d, q in serie.items()],
    }


ORDEM_URGENCIA = {'comprar_agora': 0, 'em_breve': 1, 'ok': 2}


def sugerir_reposicao(
    db: Session, usuario: Usuarios, prazo_entrega: int, dias_cobertura: int, apenas_necessarios: bool,
) -> dict:
    """Quanto comprar de cada produto para chegar ao fim de `prazo_entrega + dias_cobertura` dias
    sem faltar, com estoque de segurança de ~95% e respeitando o estoque mínimo."""
    exigir_cargo(usuario, *GESTORES)
    produtos = _produtos(db, usuario)
    parametros = {'prazo_entrega': prazo_entrega, 'dias_cobertura': dias_cobertura, 'metodo': METODO}
    if produtos.empty:
        return {'parametros': parametros,
                'resumo': {'produtos_analisados': 0, 'comprar_agora': 0, 'custo_total_estimado': 0.0},
                'itens': []}

    hoje = hoje_local()
    horizonte = prazo_entrega + dias_cobertura
    r = _prever(_serie_diaria(db, usuario, produtos, hoje), horizonte, hoje)
    previsao = r['previsao']

    demanda_prazo = previsao.iloc[:prazo_entrega].sum()
    demanda_total = previsao.sum()
    seguranca = Z_SEGURANCA_95 * r['desvio'] * math.sqrt(max(prazo_entrega, 1))
    ponto_pedido = demanda_prazo + seguranca

    itens = []
    for pid, p in produtos.iterrows():
        estoque, estoque_min = int(p['estoque']), int(p['estoque_min'])
        necessario = demanda_total[pid] + seguranca[pid] - estoque
        sugerido = max(math.ceil(round(necessario, 6)), estoque_min - estoque, 0)
        ruptura = _data_ruptura(previsao[pid], estoque)

        if estoque <= ponto_pedido[pid] or estoque <= estoque_min:
            urgencia = 'comprar_agora'
        elif ruptura and (ruptura - hoje).days <= prazo_entrega + 7:
            urgencia = 'em_breve'
        else:
            urgencia = 'ok'

        if apenas_necessarios and sugerido == 0:
            continue

        dias_hist = int(r['dias_hist'][pid])
        itens.append({
            'produto_id': int(pid),
            'produto': p['produto'],
            'codigo': p['codigo'],
            'estoque_atual': estoque,
            'estoque_min': estoque_min,
            'demanda_prevista': _arredondar(demanda_total[pid]),
            'ponto_de_pedido': _arredondar(ponto_pedido[pid]),
            'estoque_seguranca': _arredondar(seguranca[pid]),
            'quantidade_sugerida': int(sugerido),
            'custo_estimado': _arredondar(sugerido * p['preco_compra']),
            'data_ruptura_estimada': ruptura,
            'urgencia': urgencia,
            'confianca': _confianca(dias_hist, float(r['total_hist'][pid])),
        })

    itens.sort(key=lambda i: (ORDEM_URGENCIA[i['urgencia']], i['data_ruptura_estimada'] or date.max, i['produto']))

    return {
        'parametros': parametros,
        'resumo': {
            'produtos_analisados': len(produtos),
            'comprar_agora': sum(1 for i in itens if i['urgencia'] == 'comprar_agora'),
            'custo_total_estimado': _arredondar(sum(i['custo_estimado'] for i in itens)),
        },
        'itens': itens,
    }
