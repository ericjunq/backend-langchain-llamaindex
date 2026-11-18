from typing import Optional
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from schemas.produto_schema import FiltrarProdutos, ProdutoReposicaoEstoque, ProdutoSchema, ProdutoUpdate
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from models.vendas_model import ItemVendas
from security.permissoes import exigir_empresa, exigir_cargo, GESTORES
from utils.normalizar_nome import normalizar_nome
from utils.data_filter import IntervaloData, filtros_intervalo
from utils.paginacao import Paginacao

def _query_ativos(db: Session, usuario: Usuarios):
    return db.query(Produtos).filter(
        Produtos.empresa_id == usuario.empresa_id,
        Produtos.ativo.is_(True)
    )

def _buscar_produto(id: int, db: Session, usuario: Usuarios) -> Produtos:
    produto = _query_ativos(db, usuario).filter(Produtos.id == id).first()
    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    return produto

def cadastrar_produto(produtoschema: ProdutoSchema, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, *GESTORES, detail='Você não tem permissão para cadastrar produtos')

    nome_normalizado = normalizar_nome(produtoschema.nome)
    if not nome_normalizado:
        raise HTTPException(status_code=400, detail='Nome do produto inválido')

    existente = db.query(Produtos.ativo).filter(
        Produtos.empresa_id == usuario.empresa_id,
        Produtos.nome_normalizado == nome_normalizado
    ).first()
    if existente:
        detalhe = 'Já existe um produto com esse nome'
        if not existente.ativo:
            detalhe += ' (desativado)'
        raise HTTPException(status_code=409, detail=detalhe)

    produto = Produtos(
        **produtoschema.model_dump(),
        nome_normalizado=nome_normalizado,
        empresa_id=usuario.empresa_id
    )
    db.add(produto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Já existe um produto com esse nome')
    db.refresh(produto)

    return produto

def editar_produto(id: int, dados: ProdutoUpdate, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, *GESTORES, detail='Você não tem permissão para fazer isso')
    produto = _buscar_produto(id, db, usuario)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)

    return produto

def deletar_produto(id: int, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, *GESTORES, detail='Você não tem permissão para fazer isso')
    produto = _buscar_produto(id, db, usuario)

    tem_vendas = db.query(ItemVendas.id).filter(ItemVendas.produto_id == produto.id).first() is not None

    if tem_vendas:
        # Mantém o histórico de vendas e relatórios; só some das listagens e novas vendas.
        produto.ativo = False
        db.commit()
        return {'message': 'Produto possui vendas: foi desativado em vez de apagado'}

    db.delete(produto)
    db.commit()
    return {'message': 'Produto deletado com sucesso'}

def repor_estoque(id: int, dados: ProdutoReposicaoEstoque, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, *GESTORES, detail='Você não tem permissão para repor estoque')

    # FOR UPDATE: evita perder uma reposição que aconteça junto com uma venda.
    produto = _query_ativos(db, usuario).filter(Produtos.id == id).with_for_update().first()
    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')

    produto.quantidade += dados.quantidade
    db.commit()
    db.refresh(produto)

    return produto

def listar_produtos(
    paginacao: Paginacao,
    db: Session,
    usuario: Usuarios,
    intervalo: Optional[IntervaloData] = None,
):
    exigir_empresa(usuario)
    query = _query_ativos(db, usuario).filter(*filtros_intervalo(Produtos.created_at, intervalo))
    return paginacao.aplicar(query.order_by(Produtos.created_at.desc(), Produtos.id.desc())).all()

def buscar_produto_por_id(id: int, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    return _buscar_produto(id, db, usuario)

def buscar_produto(filtros: FiltrarProdutos, paginacao: Paginacao, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    query = _query_ativos(db, usuario)

    if filtros.nome and filtros.nome.strip():
        query = query.filter(Produtos.nome_normalizado.like(f"%{normalizar_nome(filtros.nome)}%"))
    if filtros.codigo_produto and filtros.codigo_produto.strip():
        query = query.filter(Produtos.codigo_produto == filtros.codigo_produto.strip().upper())
    if filtros.preco_compra is not None:
        query = query.filter(Produtos.preco_compra == filtros.preco_compra)
    if filtros.preco_venda is not None:
        query = query.filter(Produtos.preco_venda == filtros.preco_venda)
    if filtros.estoque_min is not None:
        query = query.filter(Produtos.estoque_min == filtros.estoque_min)
    if filtros.abaixo_estoque_min:
        query = query.filter(Produtos.quantidade <= Produtos.estoque_min)

    return paginacao.aplicar(query.order_by(Produtos.nome, Produtos.id)).all()
