from collections import defaultdict
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from schemas.venda_schema import VendaSchema, CancelarVenda, FiltroVendas
from models.cliente_model import Clientes
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from models.vendas_model import Vendas, ItemVendas
from security.permissoes import exigir_empresa, exigir_membro, exigir_proprio_se_funcionario
from utils.enums import CargosEnum, StatusVenda
from utils.data_filter import IntervaloData, filtros_intervalo
from utils.paginacao import Paginacao
import services.auditoria_service as auditoria

def _travar_produtos(db: Session, ids, empresa_id: Optional[int] = None, so_ativos: bool = False) -> dict:
    """Busca vários produtos numa consulta só, com FOR UPDATE.
    A ordem por id evita deadlock entre duas vendas com os mesmos produtos."""
    query = db.query(Produtos).filter(Produtos.id.in_(ids))
    if empresa_id is not None:
        query = query.filter(Produtos.empresa_id == empresa_id)
    if so_ativos:
        query = query.filter(Produtos.ativo.is_(True))
    return {p.id: p for p in query.order_by(Produtos.id).with_for_update().all()}

def criar_venda(vendaschema: VendaSchema, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)

    if vendaschema.cliente_id is not None:
        cliente = db.query(Clientes.id).filter(
            Clientes.id == vendaschema.cliente_id,
            Clientes.empresa_id == usuario.empresa_id,
            Clientes.status.is_(True)
        ).first()
        if cliente is None:
            raise HTTPException(status_code=404, detail='Cliente não encontrado')

    # Junta itens repetidos do mesmo produto.
    quantidades = defaultdict(int)
    for item in vendaschema.itens:
        quantidades[item.produto_id] += item.quantidade

    produtos = _travar_produtos(db, quantidades.keys(), usuario.empresa_id, so_ativos=True)
    faltando = sorted(set(quantidades) - produtos.keys())
    if faltando:
        raise HTTPException(status_code=404, detail=f'Produto(s) não encontrado(s): {faltando}')

    venda = Vendas(
        descricao=vendaschema.descricao,
        cliente_id=vendaschema.cliente_id,
        usuario_id=usuario.id,
        empresa_id=usuario.empresa_id,
        forma_pagamento=vendaschema.forma_pagamento,
        desconto=vendaschema.desconto,
    )

    valor_total = Decimal('0')
    for produto_id, quantidade in quantidades.items():
        produto = produtos[produto_id]
        if produto.quantidade < quantidade:
            raise HTTPException(status_code=409, detail=f'Quantidade de {produto.nome} indisponível')

        subtotal = produto.preco_venda * quantidade
        venda.itens.append(ItemVendas(
            produto_id=produto.id,
            quantidade=quantidade,
            preco_unitario=produto.preco_venda,
            custo_unitario=produto.preco_compra,
            subtotal=subtotal
        ))
        produto.quantidade -= quantidade
        valor_total += subtotal

    if vendaschema.desconto > valor_total:
        raise HTTPException(status_code=400, detail="Desconto maior que o valor da venda")

    venda.valor_total = valor_total
    venda.valor_final = valor_total - vendaschema.desconto

    db.add(venda)
    db.flush()
    auditoria.registrar(db, 'venda.criada', usuario=usuario, entidade='venda', entidade_id=venda.id,
                        categoria=auditoria.VENDA,
                        detalhes={'valor_final': venda.valor_final, 'itens': len(venda.itens),
                                  'forma_pagamento': venda.forma_pagamento})
    db.commit()
    db.refresh(venda)

    return venda

def cancelar_venda(id: int, cancelamento: CancelarVenda, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)

    venda = db.query(Vendas).filter(
        Vendas.id == id,
        Vendas.empresa_id == usuario.empresa_id,
    ).with_for_update().first()
    if venda is None:
        raise HTTPException(status_code=404, detail='Venda não encontrada')

    if usuario.cargo == CargosEnum.funcionario and venda.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para cancelar essa venda")

    if venda.status == StatusVenda.cancelada:
        raise HTTPException(status_code=400, detail='Venda já cancelada')

    # Devolve o estoque: 1 consulta para os itens + 1 para os produtos (sem N+1).
    produtos = _travar_produtos(db, [item.produto_id for item in venda.itens])
    for item in venda.itens:
        produto = produtos.get(item.produto_id)
        if produto:
            produto.quantidade += item.quantidade

    venda.status = StatusVenda.cancelada
    venda.motivo_cancelamento = cancelamento.motivo_cancelamento
    auditoria.registrar(db, 'venda.cancelada', usuario=usuario, entidade='venda', entidade_id=venda.id,
                        categoria=auditoria.VENDA,
                        detalhes={'motivo': cancelamento.motivo_cancelamento, 'valor_final': venda.valor_final})

    db.commit()
    db.refresh(venda)

    return venda

def _query_vendas(db: Session, usuario: Usuarios):
    return (
        db.query(Vendas)
        .options(selectinload(Vendas.itens))  # itens de todas as vendas em 1 consulta extra
        .filter(Vendas.empresa_id == usuario.empresa_id)
    )

def obter_venda(id: int, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    venda = _query_vendas(db, usuario).filter(Vendas.id == id).first()
    if venda is None:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    exigir_proprio_se_funcionario(usuario, venda.usuario_id, 'Você só pode ver suas próprias vendas')
    return venda

def listar_vendas(
    filtro: FiltroVendas,
    db: Session,
    usuario: Usuarios,
    paginacao: Paginacao,
    intervalo: Optional[IntervaloData] = None,
):
    """GET /vendas. Dono e Admin veem todas as vendas da empresa (ou de um funcionário,
    via `usuario_id`); funcionário vê só as próprias."""
    exigir_empresa(usuario)
    query = _query_vendas(db, usuario).filter(*filtros_intervalo(Vendas.created_at, intervalo))

    if usuario.cargo == CargosEnum.funcionario:
        if filtro.usuario_id is not None:
            exigir_proprio_se_funcionario(usuario, filtro.usuario_id, 'Você só pode listar suas próprias vendas')
        query = query.filter(Vendas.usuario_id == usuario.id)
    elif filtro.usuario_id is not None:
        exigir_membro(db, usuario, filtro.usuario_id)
        query = query.filter(Vendas.usuario_id == filtro.usuario_id)

    if filtro.cliente_id is not None:
        query = query.filter(Vendas.cliente_id == filtro.cliente_id)
    if filtro.status is not None:
        query = query.filter(Vendas.status == filtro.status)
    if filtro.forma_pagamento is not None:
        query = query.filter(Vendas.forma_pagamento == filtro.forma_pagamento)

    return paginacao.aplicar(query.order_by(Vendas.created_at.desc(), Vendas.id.desc())).all()
