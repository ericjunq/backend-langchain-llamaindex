from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.venda_schema import VendaReponse, VendaSchema, CancelarVenda
from security.dependencies import get_db
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from models.vendas_model import Vendas, ItemVendas
from security.security import get_current_user
from utils.enums import CargosEnum, StatusVenda

venda_router = APIRouter(prefix='/vendas', tags=['vendas'])

@venda_router.post('/criar_venda', response_model=VendaReponse)
async def criar_venda(
    vendaschema: VendaSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
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

@venda_router.patch('/cancelar_venda/{id}', response_model=VendaReponse)
async def cancelar_venda(
    id: int,
    cancelamento: CancelarVenda,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
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