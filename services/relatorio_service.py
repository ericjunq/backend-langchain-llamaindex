import pandas as pd
from models.cliente_model import Clientes
from models.produto_model import Produtos
from models.vendas_model import Vendas, ItemVendas
from models.usuario_model import Usuarios
from utils.enums import CargosEnum, StatusVenda, DataFilter as DFEnum
from schemas.filtrodata_schema import Periodo, DataFilter
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime, timezone


def _aplicar_filtro_data(query, inicio=None, datafilter=None):
    if inicio:
        return query.filter(Vendas.created_at >= inicio)
    if datafilter:
        return query.filter(
            Vendas.created_at >= datafilter.data_inicial,
            Vendas.created_at <= datafilter.data_final
        )
    return query

def relatorio_vendas(
    db: Session,
    usuario: Usuarios,
    exportar: bool = False,
    periodo: Optional[Periodo] = None,
    datafilter: Optional[DataFilter] = None
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')

    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Você não tem permissão para isso')

    if periodo and datafilter:
        raise HTTPException(status_code=400, detail='Você só pode usar um filtro de data por vez')

    # --- Queries base ---
    vendas = db.query(Vendas).filter(Vendas.empresa_id == usuario.empresa_id)

    produtos = (
        db.query(Produtos.id, Produtos.nome)
        .join(ItemVendas, Produtos.id == ItemVendas.produto_id)
        .join(Vendas, Vendas.id == ItemVendas.venda_id)
        .filter(
            Vendas.empresa_id == usuario.empresa_id,
            Vendas.status != StatusVenda.cancelada
        )
    )

    funcionarios = (
        db.query(Usuarios.id, Usuarios.nome)
        .join(Vendas, Vendas.usuario_id == Usuarios.id)
        .filter(
            Vendas.empresa_id == usuario.empresa_id,
            Vendas.status != StatusVenda.cancelada,
        )
    )

    clientes = (
        db.query(Clientes.id, Clientes.nome)
        .join(Vendas, Vendas.cliente_id == Clientes.id)
        .filter(
            Vendas.empresa_id == usuario.empresa_id,
            Vendas.status != StatusVenda.cancelada,
        )
    )

    # --- Filtros de data ---
    inicio = None

    if periodo:
        agora = datetime.now(timezone.utc)
        if periodo.periodo == DFEnum.mes:
            inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif periodo.periodo == DFEnum.semestre:
            mes_inicio = 1 if agora.month <= 6 else 7
            inicio = agora.replace(month=mes_inicio, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif periodo.periodo == DFEnum.ano:
            inicio = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    vendas = _aplicar_filtro_data(vendas, inicio, datafilter)
    produtos = _aplicar_filtro_data(produtos, inicio, datafilter)
    funcionarios = _aplicar_filtro_data(funcionarios, inicio, datafilter)
    clientes = _aplicar_filtro_data(clientes, inicio, datafilter)

    # --- Métricas gerais ---
    qtde_vendas = vendas.count()

    qtde_vendas_canceladas = vendas.filter(
        Vendas.status == StatusVenda.cancelada
    ).count()

    taxa_cancelamento = (qtde_vendas_canceladas / qtde_vendas) if qtde_vendas else 0

    total_clientes = vendas.with_entities(
        func.count(func.distinct(Vendas.cliente_id))
    ).scalar() or 0

    # CORRIGIDO: .scalar() era chamado dentro de db.query()
    faturamento_total = db.query(
        func.sum(Vendas.valor_total)
    ).filter(
        Vendas.empresa_id == usuario.empresa_id,
        Vendas.status != StatusVenda.cancelada
    ).scalar() or 0

    ticket_medio = faturamento_total / qtde_vendas if qtde_vendas else 0

    # --- Top 5 Produtos ---
    qtde_itens = func.sum(ItemVendas.quantidade)
    fat_itens = func.sum(ItemVendas.subtotal)

    produtos_mais_vendidos = (
        produtos.with_entities(Produtos.nome, qtde_itens.label('total_vendido'))
        .group_by(Produtos.id, Produtos.nome)
        .order_by(qtde_itens.desc())
        .limit(5).all()
    )
    produtos_menos_vendidos = (
        produtos.with_entities(Produtos.nome, qtde_itens.label('total_vendido'))
        .group_by(Produtos.id, Produtos.nome)
        .order_by(qtde_itens.asc())
        .limit(5).all()
    )
    produtos_maior_faturamento = (
        produtos.with_entities(Produtos.nome, fat_itens.label('faturamento'))
        .group_by(Produtos.id, Produtos.nome)
        .order_by(fat_itens.desc())
        .limit(5).all()
    )
    produtos_menor_faturamento = (
        produtos.with_entities(Produtos.nome, fat_itens.label('faturamento'))
        .group_by(Produtos.id, Produtos.nome)
        .order_by(fat_itens.asc())
        .limit(5).all()
    )

    # --- Top 5 Funcionários ---
    qtde_vendas_func = func.count(Vendas.id)
    fat_func = func.sum(Vendas.valor_final)

    funcionarios_mais_vendas = (
        funcionarios.with_entities(Usuarios.nome, qtde_vendas_func.label('total_vendas'))
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(qtde_vendas_func.desc())
        .limit(5).all()
    )
    funcionarios_menos_vendas = (
        funcionarios.with_entities(Usuarios.nome, qtde_vendas_func.label('total_vendas'))
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(qtde_vendas_func.asc())
        .limit(5).all()
    )
    funcionarios_maior_faturamento = (
        funcionarios.with_entities(Usuarios.nome, fat_func.label('faturamento'))
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(fat_func.desc())
        .limit(5).all()
    )
    funcionarios_menor_faturamento = (
        funcionarios.with_entities(Usuarios.nome, fat_func.label('faturamento'))
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(fat_func.asc())
        .limit(5).all()
    )

    # --- Top 5 Clientes ---
    qtde_compras = func.count(Vendas.id)
    fat_clientes = func.sum(Vendas.valor_final)

    clientes_mais_compras = (
        clientes.with_entities(Clientes.nome, qtde_compras.label('total_compras'))
        .group_by(Clientes.id, Clientes.nome)
        .order_by(qtde_compras.desc())
        .limit(5).all()
    )
    clientes_maior_faturamento = (
        clientes.with_entities(Clientes.nome, fat_clientes.label('faturamento'))
        .group_by(Clientes.id, Clientes.nome)
        .order_by(fat_clientes.desc())
        .limit(5).all()
    )

    # --- DataFrames ---
    produtos_mais_vendidos_df = pd.DataFrame(produtos_mais_vendidos, columns=['produto', 'quantidade'])
    produtos_menos_vendidos_df = pd.DataFrame(produtos_menos_vendidos, columns=['produto', 'quantidade'])
    produtos_maior_faturamento_df = pd.DataFrame(produtos_maior_faturamento, columns=['produto', 'valor_total'])
    produtos_menor_faturamento_df = pd.DataFrame(produtos_menor_faturamento, columns=['produto', 'valor_total'])
    funcionarios_mais_vendas_df = pd.DataFrame(funcionarios_mais_vendas, columns=['nome', 'quantidade'])
    funcionarios_menos_vendas_df = pd.DataFrame(funcionarios_menos_vendas, columns=['nome', 'quantidade'])
    funcionarios_maior_faturamento_df = pd.DataFrame(funcionarios_maior_faturamento, columns=['nome', 'valor_total'])
    funcionarios_menor_faturamento_df = pd.DataFrame(funcionarios_menor_faturamento, columns=['nome', 'valor_total'])
    clientes_mais_compras_df = pd.DataFrame(clientes_mais_compras, columns=['nome', 'quantidade'])
    clientes_maior_faturamento_df = pd.DataFrame(clientes_maior_faturamento, columns=['nome', 'valor_total'])

    resumo = {
        'total_vendas': qtde_vendas,
        'total_vendas_canceladas': qtde_vendas_canceladas,
        'taxa_cancelamento': round(taxa_cancelamento, 4),
        'total_clientes': total_clientes,
        'ticket_medio': round(ticket_medio, 2),
        'faturamento_total': round(faturamento_total, 2),
    }

    if exportar:
        caminho = 'Relatorio.xlsx'
        resumo_df = pd.DataFrame([resumo])
        with pd.ExcelWriter(caminho) as writer:
            resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
            produtos_mais_vendidos_df.to_excel(writer, sheet_name='Prod Mais Vendidos', index=False)
            produtos_menos_vendidos_df.to_excel(writer, sheet_name='Prod Menos Vendidos', index=False)
            produtos_maior_faturamento_df.to_excel(writer, sheet_name='Prod Maior Fat', index=False)
            produtos_menor_faturamento_df.to_excel(writer, sheet_name='Prod Menor Fat', index=False)
            funcionarios_mais_vendas_df.to_excel(writer, sheet_name='Func Mais Vendas', index=False)
            funcionarios_menos_vendas_df.to_excel(writer, sheet_name='Func Menos Vendas', index=False)
            funcionarios_maior_faturamento_df.to_excel(writer, sheet_name='Func Maior Fat', index=False)
            funcionarios_menor_faturamento_df.to_excel(writer, sheet_name='Func Menor Fat', index=False)
            clientes_mais_compras_df.to_excel(writer, sheet_name='Clientes Mais Compras', index=False)
            clientes_maior_faturamento_df.to_excel(writer, sheet_name='Clientes Maior Fat', index=False)
        return {'exportado': True, 'caminho': caminho}

    return {
        'resumo': resumo,
        'produtos_mais_vendidos': produtos_mais_vendidos_df.to_dict(orient='records'),
        'produtos_menos_vendidos': produtos_menos_vendidos_df.to_dict(orient='records'),
        'produtos_maior_faturamento': produtos_maior_faturamento_df.to_dict(orient='records'),
        'produtos_menor_faturamento': produtos_menor_faturamento_df.to_dict(orient='records'),
        'funcionarios_mais_vendas': funcionarios_mais_vendas_df.to_dict(orient='records'),
        'funcionarios_menos_vendas': funcionarios_menos_vendas_df.to_dict(orient='records'),
        'funcionarios_maior_faturamento': funcionarios_maior_faturamento_df.to_dict(orient='records'),
        'funcionarios_menor_faturamento': funcionarios_menor_faturamento_df.to_dict(orient='records'),
        'clientes_mais_compras': clientes_mais_compras_df.to_dict(orient='records'),
        'clientes_maior_faturamento': clientes_maior_faturamento_df.to_dict(orient='records'),
    }