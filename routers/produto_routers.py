from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.produto_schema import FiltrarProdutos, ProdutoReponse, ProdutoReposicaoEstoque, ProdutoSchema, ProdutoUpdate
from security.dependencies import get_db
from models.usuario_model import Usuarios
from security.security import get_current_user
from schemas.filtrodata_schema import DataFilter, Periodo
from typing import List
from utils.data_filter import get_data_filter
import services.produto_service

produto_router = APIRouter(prefix='/produtos', tags=['produtos'])

@produto_router.post('/cadastrar_produto', response_model=ProdutoReponse)
async def cadastrar_produto(
    produtoschema: ProdutoSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.produto_service.cadastrar_produto(produtoschema, db, usuario)

@produto_router.post('/editar_produto/{id}', response_model=ProdutoReponse)
async def editar_produto(
    id: int,
    dados: ProdutoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.produto_service.editar_produto(id, dados, db, usuario)

@produto_router.delete('/deletar_produto/{id}')
async def deletar_produto(
    id:int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.produto_service.deletar_produto(id, db, usuario)

@produto_router.patch('/repor_estoque/{id}', response_model=ProdutoReponse)
async def repor_estoque(
    id: int,
    dados: ProdutoReposicaoEstoque,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
): 
    return services.produto_service.repor_estoque(id, dados, db, usuario)

@produto_router.get('/listar_produtos', response_model=List[ProdutoReponse])
async def listar_produtos(
    datafilter: DataFilter = Depends(get_data_filter),
    periodo: Periodo = Depends(),
    db: Session=Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.produto_service.listar_produtos(datafilter, periodo, db, usuario)

@produto_router.get('/buscar_produto_por_id/{id}', response_model=ProdutoReponse)
async def buscar_produto_por_id(
    id: int, 
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.produto_service.buscar_produto_por_id(id, db, usuario)

@produto_router.get('/buscar_produto', response_model=List[ProdutoReponse])
async def buscar_produto(
    filtros: FiltrarProdutos = Depends(),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.produto_service.buscar_produto(filtros, db, usuario)