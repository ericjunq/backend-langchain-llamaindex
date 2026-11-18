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

@produto_router.post('', response_model=ProdutoResponse, status_code=201)
def criar_produto(
    dados: ProdutoSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_produto(dados, db, usuario)

# Produto não tem dado pessoal: todos os filtros podem ir na URL.
@produto_router.get('', response_model=List[ProdutoResponse])
def listar_produtos(
    filtros: FiltrarProdutos = Depends(),
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_produtos(filtros, paginacao, db, usuario, intervalo)

@produto_router.get('/{id}', response_model=ProdutoResponse)
def obter_produto(id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.obter_produto(id, db, usuario)

@produto_router.patch('/{id}', response_model=ProdutoResponse)
def editar_produto(
    id: int,
    dados: ProdutoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_produto(id, dados, db, usuario)

@produto_router.delete('/{id}')
def deletar_produto(id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.deletar_produto(id, db, usuario)

# Entrada de estoque (soma à quantidade atual).
@produto_router.post('/{id}/reposicao', response_model=ProdutoResponse)
def repor_estoque(
    id: int,
    dados: ProdutoReposicaoEstoque,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.repor_estoque(id, dados, db, usuario)
