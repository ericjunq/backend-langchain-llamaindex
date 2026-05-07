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
from fastapi.responses import FileResponse
from datetime import datetime, timezone

def relatorio_vendas(
    db: Session,
    usuario: Usuarios,
    exportar: bool = False,
    periodo: Optional[Periodo]=None,
    datafilter: Optional[DataFilter]=None
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Você não tem permissão para isso')
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail='Você só pode usar um filtro de data por vez')
    
    vendas = db.query(Vendas).filter(
        Vendas.empresa_id == usuario.empresa_id
        )
    
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

    if periodo:
        inicio = datetime.now(timezone.utc)
        if periodo.periodo == DFEnum.mes:
            inicio = inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            vendas = vendas.filter(
                Vendas.created_at >= inicio
            )
            produtos = produtos.filter(
                Vendas.created_at >= inicio
            )
            funcionarios = funcionarios.filter(
                Vendas.created_at >= inicio
            )
        
        elif periodo.periodo == DFEnum.semestre:
            if inicio.month <= 6:
                inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                inicio = inicio.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
            vendas = vendas.filter(
                Vendas.created_at >= inicio
            )
            produtos = produtos.filter(
                Vendas.created_at >= inicio
            )
            funcionarios = funcionarios.filter(
                Vendas.created_at >= inicio
            )
            clientes = clientes.filter(
                Vendas.created_at >= inicio
            )
        
        elif periodo.periodo == DFEnum.ano:
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            vendas = vendas.filter(
                Vendas.created_at >= inicio
            )
            produtos = produtos.filter(
                Vendas.created_at >= inicio
            )
            funcionarios = funcionarios.filter(
                Vendas.created_at >= inicio
            )
            clientes = clientes.filter(
                Vendas.created_at >= inicio
            )
    
    if datafilter:
        vendas = vendas.filter(
            Vendas.created_at >= datafilter.data_inicial,
            Vendas.created_at <= datafilter.data_final
        )
        produtos = produtos.filter(
                Vendas.created_at >= datafilter.data_inicial,
                Vendas.created_at <= datafilter.data_final
            )
        funcionarios = funcionarios.filter(
            Vendas.created_at >= datafilter.data_inicial,
            Vendas.created_at <= datafilter.data_final
        )
        clientes = clientes.filter(
                Vendas.created_at >= inicio
            )

    # Quantidade de Vendas (concluidas e canceladas)
    qtde_vendas = vendas.count()
    
    qtde_vendas_canceladas = vendas.filter(
        Vendas.status == StatusVenda.cancelada
    ).count()
    
    taxa_cancelamento_vendas = qtde_vendas_canceladas / qtde_vendas

    # Total de clientes
    total_clientes = vendas.group_by(
        Vendas.cliente_id
        ).count()
    
    # Faturamento total
    faturamento_total = db.query(
        func(Vendas.valor_total)
        ).scalar()
    
    # Ticket Médio
    ticked_medio = faturamento_total / qtde_vendas

    # Top 5 produtos mais vendidos
    total_vendido = func.sum(ItemVendas.quantidade)
    produtos_mais_vendidos = (
        produtos.with_entities(
            Produtos.nome,
            total_vendido.label('total_vendido')
        )
        .group_by(Produtos.id, Produtos.nome)
        .order_by(total_vendido.desc())
        .limit(5)
        .all()
    )

    # Top 5 produtos menos vendidos
    produtos_menos_vendidos = (
        produtos.with_entities(
            Produtos.nome,
            total_vendido.label('total_vendido')
        )
        .group_by(Produtos.id, Produtos.nome)
        .order_by(total_vendido.asc())
        .limit(5)
        .all()
    )

    # Top 5 produtos de maior faturamento
    faturamento = func.sum(ItemVendas.subtotal)
    produtos_maior_faturamento = (
        produtos.with_entities(
            Produtos.nome,
            faturamento.label('faturamento')
        )
        .group_by(Produtos.id, Produtos.nome)
        .order_by(faturamento.desc())
        .limit(5)
        .all()
    )

    # Top 5 produtos de menor faturamento
    produtos_menor_faturamento = (
        produtos.with_entities(
            Produtos.nome,
            faturamento.label('faturamento')
        )
        .group_by(Produtos.id, Produtos.nome)
        .order_by(faturamento.asc())
        .limit(5)
        .all()
    )
    
    # Top 5 Funcionários com mais vendas
    total_vendas = func.count(Vendas.id)
    funcionarios_mais_vendas = (
        funcionarios.with_entities(
            Usuarios.nome,
            total_vendas.label('total_vendas')
        )
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(total_vendas.desc())
        .limit(5)
        .all()
    )
    # Top 5 Funcionários com menos vendas
    funcionarios_menos_vendas = (
        funcionarios.with_entities(
            Usuarios.nome,
            total_vendas.label('total_vendas')
        )
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(total_vendas.desc())
        .limit(5)
        .all()
        )

    # Top 5 Funcionários com maior faturamento
    faturamento = func.sum(Vendas.valor_final)
    funcionarios_maior_faturamento = (
        funcionarios.with_entities(
            Usuarios.nome,
            faturamento.label('faturamento')
        )
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(faturamento.desc())
        .limit(5)
        .all()
    )

    # Top 5 funcionários com menor faturamento
    funcionarios_menor_faturamento = (
        funcionarios.with_entities(
            Usuarios.nome,
            faturamento.label('faturamento')
        )
        .group_by(Usuarios.id, Usuarios.nome)
        .order_by(faturamento.desc())
        .limit(5)
        .all()
    )

    # Top 5 clientes que mais compraram
    total_compras = func.count(Vendas.id)
    clientes_mais_compras = (
        clientes.with_entities(
            Clientes.nome,
            total_compras.label('total_compras')
        )
        .group_by(Clientes.id, Clientes.nome)
        .order_by(total_compras.desc())
        .limit(5)
        .all()
    )

    # Top 5 clientes com maior faturamento
    faturamento = func.sum(Vendas.valor_final)
    clientes_maior_faturamento = (
        clientes.with_entities(
            Clientes.nome,
            faturamento.label('faturamento')
        )
        .group_by(Clientes.id, Clientes.nome)
        .order_by(faturamento.desc())
        .limit(5)
        .all()
        )

    clientes_mais_compras_df = pd.DataFrame(clientes_mais_compras, columns=['nome', 'quantidade'])
    clientes_maior_faturamento_df = pd.DataFrame(clientes_mais_compras, columns=['nome', 'quantidade'])
    produtos_mais_vendidos_df = pd.DataFrame(produtos_mais_vendidos, columns=['produto', 'quantidade'])
    produtos_menos_vendidos_df = pd.DataFrame(produtos_menos_vendidos, columns=['produto', 'quantidade'])
    produtos_maior_faturamento_df = pd.DataFrame(produtos_maior_faturamento, columns=['produtos', 'valor_total'])
    produtos_menor_faturamento_df = pd.DataFrame(produtos_menor_faturamento, columns=['produtos', 'valor_total'])
    funcionarios_mais_vendas_df = pd.DataFrame(funcionarios_mais_vendas, columns=['nome', 'quantidade'])
    funcionarios_menos_vendas_df = pd.DataFrame(funcionarios_menos_vendas, columns=['nome', 'quantidade'])
    funcionarios_maior_faturamento_df = pd.DataFrame(funcionarios_maior_faturamento, columns=['nome', 'valor_total'])
    funcionarios_menos_faturamento_df = pd.DataFrame(funcionarios_menor_faturamento, columns=['nome', 'valor_total'])

    vendas_df = pd.DataFrame(
        'Total de vendas': qtde_vendas,
        'Total de vendas canceladas', qtde_vendas_canceladas,
        'Taxa de cancelamento de vendas': taxa_cancelamento_vendas,
        'Total de clientes': total_clientes,
        'Clientes que compraram mais': clientes_mais_compras_df,
        'Clientes de maior faturamento': clientes_maior_faturamento_df,
        'Produtos mais vendidos': produtos_maior_faturamento_df,
        'Produtos menos vendidos': produtos_menos_vendidos_df,
        'Produtos com maior faturamento': produtos_maior_faturamento_df,
        'Produtos com menor faturamento': produtos_menor_faturamento_df,
        'Funcionarios com mais vendas': funcionarios_mais_vendas_df,
        'Funcionarios com menos vendas': funcionarios_menos_vendas_df,
        'Funcionarios com maior faturamento': funcionarios_maior_faturamento_df,
        'Funcionarios com menor faturamento': funcionarios_menos_faturamento_df
    )

    if vendas_df.empty:
        return {}
    
    if exportar:
        vendas_df.to_excel('Relatorio de vendas.xlsx')
        return FileResponse(
            'Relatorio de vendas.xlsx',
            filename='Relatorio de vendas.xlsx',
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    return vendas_df
