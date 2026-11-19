"""Painel inicial: tudo o que a tela mostra numa chamada só (menos idas e voltas do frontend).

Todos: as minhas vendas (hoje e no mês) e as minhas últimas vendas.
Dono/admin: faturamento do mês × mesmo período do mês anterior, vendas por dia (30 dias),
estoque abaixo do mínimo e reposição por nível de necessidade.

Desempenho: 2 consultas para todos; +3 consultas agregadas (com índice empresa/data) + a
previsão de reposição (2 consultas) para gestores. Dias sem venda são preenchidos em Python.
LGPD: cliente aparece abreviado ("Maria S."); valores de reposição são estimativas.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from models.cliente_model import Clientes
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from models.vendas_model import Vendas
from security.permissoes import GESTORES, exigir_empresa
from security.settings import settings
from services.chat_ferramentas import nome_curto
from services.previsao_service import _fuso, hoje_local, sugerir_reposicao
from utils.enums import StatusVenda

DIAS_GRAFICO = 30
LIMITE_LISTAS = 5


def _inicio_do_dia(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=_fuso())


def _dinheiro(valor) -> float:
    return round(float(valor or 0), 2)


def _mes_anterior(dia: date) -> tuple[date, date]:
    """(1º dia do mês anterior, mesmo dia do mês anterior, limitado ao fim daquele mês)."""
    primeiro_atual = dia.replace(day=1)
    fim_anterior = primeiro_atual - timedelta(days=1)
    return fim_anterior.replace(day=1), fim_anterior.replace(day=min(dia.day, fim_anterior.day))


def montar(db: Session, usuario: Usuarios) -> dict:
    exigir_empresa(usuario)
    hoje = hoje_local()
    inicio_hoje = _inicio_do_dia(hoje)
    inicio_mes = _inicio_do_dia(hoje.replace(day=1))
    concluida = Vendas.status == StatusVenda.concluida
    da_empresa = Vendas.empresa_id == usuario.empresa_id

    # 1) Minhas vendas hoje e no mês: uma consulta com FILTER.
    q_hoje, v_hoje, q_mes, v_mes = db.query(
        func.count(Vendas.id).filter(Vendas.created_at >= inicio_hoje),
        func.sum(Vendas.valor_final).filter(Vendas.created_at >= inicio_hoje),
        func.count(Vendas.id),
        func.sum(Vendas.valor_final),
    ).filter(da_empresa, concluida, Vendas.usuario_id == usuario.id, Vendas.created_at >= inicio_mes).one()

    # 2) Minhas últimas vendas (com o nome do cliente abreviado).
    ultimas = (
        db.query(Vendas.id, Vendas.created_at, Vendas.valor_final, Vendas.status, Clientes.nome)
        .outerjoin(Clientes, Clientes.id == Vendas.cliente_id)
        .filter(da_empresa, Vendas.usuario_id == usuario.id)
        .order_by(Vendas.created_at.desc(), Vendas.id.desc())
        .limit(LIMITE_LISTAS).all()
    )

    resposta = {
        'minhas_vendas': {
            'hoje': {'quantidade': q_hoje, 'total': _dinheiro(v_hoje)},
            'mes': {'quantidade': q_mes, 'total': _dinheiro(v_mes)},
        },
        'minhas_ultimas_vendas': [
            {'id': v.id, 'data': v.created_at, 'valor': _dinheiro(v.valor_final), 'status': v.status.value,
             'cliente': nome_curto(v.nome)}
            for v in ultimas
        ],
        'empresa': None,
    }
    if usuario.cargo in GESTORES:
        resposta['empresa'] = _visao_da_empresa(db, usuario, hoje, inicio_mes, concluida, da_empresa)
    return resposta


def _visao_da_empresa(db, usuario, hoje, inicio_mes, concluida, da_empresa) -> dict:
    inicio_anterior, mesmo_dia_anterior = _mes_anterior(hoje)
    corte_anterior = _inicio_do_dia(mesmo_dia_anterior + timedelta(days=1))

    # 3) Faturamento do mês × mesmo período do mês anterior (comparação justa com o mês em andamento).
    fat_mes, vendas_mes, fat_anterior = db.query(
        func.sum(Vendas.valor_final).filter(Vendas.created_at >= inicio_mes),
        func.count(Vendas.id).filter(Vendas.created_at >= inicio_mes),
        func.sum(Vendas.valor_final).filter(Vendas.created_at < corte_anterior),
    ).filter(da_empresa, concluida, Vendas.created_at >= _inicio_do_dia(inicio_anterior)).one()
    fat_mes, fat_anterior = _dinheiro(fat_mes), _dinheiro(fat_anterior)

    # 4) Vendas por dia (no fuso da empresa); dias sem venda entram com zero.
    primeiro_dia = hoje - timedelta(days=DIAS_GRAFICO - 1)
    dia = cast(func.timezone(settings.fuso_horario, Vendas.created_at), Date)
    por_dia = {
        d: (q, total) for d, q, total in
        db.query(dia, func.count(Vendas.id), func.sum(Vendas.valor_final))
        .filter(da_empresa, concluida, Vendas.created_at >= _inicio_do_dia(primeiro_dia))
        .group_by(dia).all()
    }
    serie = []
    for i in range(DIAS_GRAFICO):
        d = primeiro_dia + timedelta(days=i)
        q, total = por_dia.get(d, (0, 0))
        serie.append({'data': d, 'quantidade': q, 'total': _dinheiro(total)})

    # 5) Estoque abaixo do mínimo: total + os mais críticos (maior falta primeiro).
    abaixo = (
        db.query(Produtos.id, Produtos.nome, Produtos.quantidade, Produtos.estoque_min)
        .filter(Produtos.empresa_id == usuario.empresa_id, Produtos.ativo.is_(True),
                Produtos.quantidade <= Produtos.estoque_min)
    )
    total_abaixo = abaixo.count()
    criticos = abaixo.order_by((Produtos.quantidade - Produtos.estoque_min).asc(), Produtos.nome).limit(LIMITE_LISTAS).all()

    reposicao = sugerir_reposicao(db, usuario, prazo_entrega=7, dias_cobertura=30, apenas_necessarios=True)

    return {
        'faturamento_mes': fat_mes,
        'faturamento_mesmo_periodo_mes_anterior': fat_anterior,
        'variacao_pct': round((fat_mes - fat_anterior) / fat_anterior * 100, 1) if fat_anterior else None,
        'vendas_mes': vendas_mes,
        'vendas_por_dia': serie,
        'estoque_abaixo_minimo': {
            'total': total_abaixo,
            'itens': [{'id': p.id, 'produto': p.nome, 'estoque': p.quantidade, 'estoque_min': p.estoque_min}
                      for p in criticos],
        },
        'reposicao': {
            'por_necessidade': reposicao['resumo']['por_necessidade'],
            'gasto_estimado_reposicao': reposicao['resumo']['gasto_estimado_reposicao'],
            'comprar_agora': [
                {'produto_id': i['produto_id'], 'produto': i['produto'], 'comprar': i['quantidade_sugerida']}
                for i in reposicao['itens'] if i['necessidade'] == 'comprar_agora'
            ][:LIMITE_LISTAS],
        },
    }
