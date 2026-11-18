from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.produto_schema import FiltrarProdutos, ProdutoResponse, ProdutoReposicaoEstoque, ProdutoSchema, ProdutoUpdate
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
from utils.data_filter import IntervaloData, get_intervalo_data
from utils.paginacao import Paginacao, get_paginacao
import services.produto_service as service

produto_router = APIRouter(prefix='/produtos', tags=['produtos'])

@produto_router.post('/cadastrar_produto', response_model=ProdutoResponse, status_code=201)
def cadastrar_produto(
    produtoschema: ProdutoSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.cadastrar_produto(produtoschema, db, usuario)

@produto_router.patch('/editar_produto/{id}', response_model=ProdutoResponse)
def editar_produto(
    id: int,
    dados: ProdutoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_produto(id, dados, db, usuario)

@produto_router.delete('/deletar_produto/{id}')
def deletar_produto(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.deletar_produto(id, db, usuario)

@produto_router.patch('/repor_estoque/{id}', response_model=ProdutoResponse)
def repor_estoque(
    id: int,
    dados: ProdutoReposicaoEstoque,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.repor_estoque(id, dados, db, usuario)

@produto_router.get('/listar_produtos', response_model=List[ProdutoResponse])
def listar_produtos(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_produtos(paginacao, db, usuario, intervalo)

@produto_router.get('/buscar_produto_por_id/{id}', response_model=ProdutoResponse)
def buscar_produto_por_id(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.buscar_produto_por_id(id, db, usuario)

@produto_router.get('/buscar_produto', response_model=List[ProdutoResponse])
def buscar_produto(
    filtros: FiltrarProdutos = Depends(),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.buscar_produto(filtros, paginacao, db, usuario)
