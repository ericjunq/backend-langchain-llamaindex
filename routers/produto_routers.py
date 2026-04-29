from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.produto_schema import FiltrarProdutos, ProdutoReponse, ProdutoReposicaoEstoque, ProdutoSchema, ProdutoUpdate
from security.dependencies import get_db
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from security.security import get_current_user
from utils.enums import CargosEnum
from schemas.filtrodata_schema import DataFilter, Periodo
from typing import List
from utils.data_filter import get_data_filter
from datetime import datetime, timezone
from utils.normalizar_nome import normalizar_nome

produto_router = APIRouter(prefix='/produtos', tags=['produtos'])

@produto_router.post('/cadastrar_produto', response_model=ProdutoReponse)
async def cadastrar_produto(
    produtoschema: ProdutoSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=404, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para cadastrar produtos')
    
    nome_padronizado = normalizar_nome(produtoschema.nome)
    
    produto = Produtos(
        nome=produtoschema.nome,
        nome_normalizado=nome_padronizado,
        descricao=produtoschema.descricao,
        quantidade=produtoschema.quantidade,
        preco_compra=produtoschema.preco_compra,
        preco_venda=produtoschema.preco_venda,
        estoque_min=produtoschema.estoque_min
    )
    produto.empresa_id = usuario.empresa_id

    db.add(produto)
    db.commit()
    db.refresh(produto)

    return produto

@produto_router.post('/editar_produto/{id}', response_model=ProdutoReponse)
async def editar_produto(
    id: int,
    dados: ProdutoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para fazer isso')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    dados_update = dados.model_dump(exclude_unset=True)

    for campo, valor in dados_update.items():
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)

    return produto

@produto_router.delete('/deletar_produto/{id}')
async def deletar_produto(
    id:int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para fazer isso')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    db.delete(produto)
    db.commit()

    return {'message':'Produto deletado com sucesso'}

@produto_router.patch('/repor_estoque/{id}', response_model=ProdutoReponse)
async def repor_estoque(
    id: int,
    dados: ProdutoReposicaoEstoque,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
): 
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    nova_quantidade = dados.quantidade
    produto.quantidade += nova_quantidade

    db.commit()
    db.refresh(produto)

    return produto

@produto_router.get('/listar_produtos', response_model=List[ProdutoReponse])
async def listar_produtos(
    datafilter: DataFilter = Depends(get_data_filter),
    periodo: Periodo = Depends(),
    db: Session=Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail='Use apenas um filtro por vez')
    
    query = db.query(Produtos).filter(
        Produtos.empresa_id == usuario.empresa_id
    )

    if periodo:
        inicio = datetime.now(timezone.utc)
        if periodo.periodo == 'mes': 
            inicio = inicio.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
            query = query.filter(
                Produtos.created_at >= inicio
            )
        if periodo.periodo == 'semestre':
            inicio = inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if inicio.month <= 6:
                inicio = inicio.replace(month=1)
            else:
                inicio = inicio.replace(month=7)
            query = query.filter(
                Produtos.created_at >= inicio
            )
        if periodo.periodo == 'ano':
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Produtos.created_at >= inicio
            )

    if datafilter:
        query = query.filter(
            Produtos.created_at >= datafilter.data_inicial,
            Produtos.created_at <= datafilter.data_final
        )

    return query.all()

@produto_router.get('/buscar_produto_por_id/{id}', response_model=ProdutoReponse)
async def buscar_produto_por_id(
    id: int, 
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    return produto

@produto_router.get('/buscar_produto', response_model=List[ProdutoReponse])
async def buscar_produto(
    filtros: FiltrarProdutos = Depends(),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    query = db.query(Produtos).filter(
        Produtos.empresa_id == usuario.empresa_id
    )

    if filtros.nome and filtros.nome.strip():
        nome_normalizado = normalizar_nome(filtros.nome)
        query = query.filter(
            Produtos.nome_normalizado.ilike(f"%{nome_normalizado}%")
        )
    if filtros.codigo_produto and filtros.codigo_produto.strip():
        query = query.filter(
            Produtos.codigo_produto == filtros.codigo_produto
        )
    if filtros.preco_compra and filtros.preco_compra.strip():
        query = query.filter(
            Produtos.preco_compra == filtros.preco_compra
        )
    if filtros.preco_venda and filtros.preco_venda.strip():
        query = query.filter(
            Produtos.preco_venda == filtros.preco_venda
        )
    if filtros.estoque_min and filtros.estoque_min.strip():
        query = query.filter(
            Produtos.estoque_min == filtros.estoque_min
        )

    return query.all()