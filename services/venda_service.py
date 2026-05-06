from fastapi import HTTPException
from sqlalchemy.orm import Session
from schemas.venda_schema import VendaSchema, CancelarVenda
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from models.vendas_model import Vendas, ItemVendas
from utils.enums import CargosEnum, StatusVenda
from utils.enums import DataFilter as DFEnum
from schemas.filtrodata_schema import Periodo, DataFilter
from typing import Optional
from datetime import datetime, timezone

# Função pra criar venda
def criar_venda(
    vendaschema: VendaSchema,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    venda = Vendas(
        descricao=vendaschema.descricao,
        cliente_id=vendaschema.cliente_id,
        desconto=vendaschema.desconto,
        forma_pagamento=vendaschema.forma_pagamento
    )

    db.add(venda)
    db.flush()
    
    valor_total = 0

    for item in vendaschema.itens:
        produto = db.query(Produtos).filter(
            Produtos.id == item.produto_id,
            Produtos.empresa_id == usuario.empresa_id
        ).first()

        if produto is None:
            raise HTTPException(status_code=404, detail='Produto não encontrado')

        if produto.quantidade < item.quantidade:
            raise HTTPException(status_code=409, detail=f'Quantidade de {produto.nome} indisponivel')
        
        preco = produto.preco_venda
        subtotal = preco * item.quantidade

        item_venda = ItemVendas(
            venda_id=venda.id,
            produto_id=produto.id,
            quantidade=item.quantidade,
            preco_unitario=produto.preco_venda,
            subtotal=subtotal
        )

        db.add(item_venda)

        produto.quantidade -= item.quantidade

        valor_total += subtotal
    
    venda.valor_total = valor_total
    if venda.desconto and venda.desconto > venda.valor_total:
        raise HTTPException(status_code=400, detail="Desconto maior que o valor da venda")

    venda.valor_final = venda.valor_total - venda.desconto
    venda.usuario_id = usuario.id

    db.commit()
    db.refresh(venda)

    return venda

# Função pra cancelar venda
def cancelar_venda(
    id: int,
    cancelamento: CancelarVenda,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    venda = db.query(Vendas).filter(
        Vendas.id == id, 
        Vendas.empresa_id == usuario.empresa_id,
    ).first()
    if venda.usuario_id != usuario.id and usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail="Você não tem permissão para cancelar essa venda")
    
    if venda.status == StatusVenda.cancelada:
        raise HTTPException(status_code=400, detail='Venda já cancelada')
    venda.status = StatusVenda.cancelada
    venda.motivo_cancelamento = cancelamento.motivo_cancelamento

    itens = db.query(ItemVendas).filter(
        ItemVendas.venda_id == venda.id
    ).all()

    for item in itens:
        produto = db.query(Produtos).filter(
            Produtos.id == item.produto_id
        ).first()
        if produto:
            produto.quantidade += item.quantidade

    db.commit()
    db.refresh(venda)

    return venda

def listar_vendas(
        db: Session,
        usuario: Usuarios,
        periodo: Optional[Periodo]=None,
        datafilter: Optional[DataFilter]=None
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail="Use apenas um filtro por vez")
    
    query = db.query(Vendas).filter(
        Vendas.empresa_id == usuario.empresa_id
    )

    if periodo:
        inicio = datetime.now(timezone.utc)
        if periodo.periodo == DFEnum.mes:
            inicio = inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Vendas.created_at >= inicio
            )
        
        elif periodo.periodo == DFEnum.semestre:
            if inicio.month <= 6:
                inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                inicio = inicio.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Vendas.created_at >= inicio
            )
        
        elif periodo.periodo == DFEnum.ano:
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Vendas.created_at >= inicio
            )
    
    if datafilter:
        query = query.filter(
            Vendas.created_at >= datafilter.data_inicial,
            Vendas.created_at <= datafilter.data_final
        )

    return query.all()

# Função para listar vendas de um funcionário
# Dono e Admin podem listar todos as vendas de qualquer funcionário
# Funcionário só pode listar as próprias vendas
def listar_vendas_funcionario(
        id: int,
        db: Session,
        usuario: Usuarios,
        periodo: Optional[Periodo]=None,
        datafilter: Optional[DataFilter]=None
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail="Você não pertence a nenhuma empresa")
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail="Use apenas um filtro por vez")


    funcionario = db.query(Usuarios).filter(
        Usuarios.empresa_id == usuario.empresa_id,
        Usuarios.id == id
    ).first()

    if funcionario is None:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    if usuario.cargo == CargosEnum.funcionario and usuario.id != funcionario.id:
        raise HTTPException(status_code=403, detail='Você só pode listar suas próprias vendas')

    query = db.query(Vendas).filter(
        Vendas.empresa_id == usuario.empresa_id,
        Vendas.usuario_id == funcionario.id
    )

    if periodo:
        if periodo.periodo == DFEnum.mes:
            inicio = datetime.now(timezone.utc)
        if periodo.periodo == DFEnum.mes:
            inicio = inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Vendas.created_at >= inicio
            )
        
        elif periodo.periodo == DFEnum.semestre:
            if inicio.month <= 6:
                inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                inicio = inicio.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Vendas.created_at >= inicio
            )
        
        elif periodo.periodo == DFEnum.ano:
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Vendas.created_at >= inicio
            )
    
    if datafilter:
        query = query.filter(
            Vendas.created_at >= datafilter.data_inicial,
            Vendas.created_at <= datafilter.data_final
        )

    return query.all()