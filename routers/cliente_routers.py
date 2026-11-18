from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from schemas.cliente_schema import FiltrarCliente, ClienteCreate, ClienteResponse, ClienteUpdate
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
from utils.data_filter import IntervaloData, get_intervalo_data
from utils.paginacao import Paginacao, get_paginacao
import services.cliente_service as service

# Rotas em `def` (não `async def`): o SQLAlchemy aqui é síncrono, então o FastAPI
# roda cada requisição numa thread do pool em vez de travar o event loop.
cliente_router = APIRouter(prefix='/clientes', tags=['clientes'])

@cliente_router.post('', response_model=ClienteResponse, status_code=201)
def criar_cliente(
    dados: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_cliente(dados, db, usuario)

@cliente_router.get('', response_model=List[ClienteResponse])
def listar_clientes(
    usuario_id: Optional[int] = Query(None, description='Clientes cadastrados por um funcionário'),
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_clientes(db, usuario, paginacao, intervalo, usuario_id)

# Busca por nome/email/CPF/telefone: filtros no corpo para não expor dado pessoal na URL (LGPD).
@cliente_router.post('/busca', response_model=List[ClienteResponse])
def buscar_clientes(
    filtro: FiltrarCliente,
    usuario_id: Optional[int] = Query(None, description='Clientes cadastrados por um funcionário'),
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_clientes(db, usuario, paginacao, intervalo, usuario_id, filtro)

@cliente_router.get('/{id}', response_model=ClienteResponse)
def obter_cliente(id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.obter_cliente(id, db, usuario)

@cliente_router.patch('/{id}', response_model=ClienteResponse)
def editar_cliente(
    id: int,
    dados: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_cliente(id, dados, db, usuario)

@cliente_router.delete('/{id}')
def deletar_cliente(id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.deletar_cliente(id, db, usuario)
