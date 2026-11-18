from typing import List, Optional
from fastapi import APIRouter, Depends
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
cliente_router = APIRouter(prefix='/cliente', tags=['clientes'])

@cliente_router.post('/adicionar_cliente', response_model=ClienteResponse, status_code=201)
def adicionar_cliente(
    clienteschema: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.adicionar_cliente(clienteschema, db, usuario)

@cliente_router.patch('/editar_cliente/{id}', response_model=ClienteResponse)
def editar_cliente(
    id: int,
    dados: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_cliente(id, dados, db, usuario)

@cliente_router.delete('/deletar_cliente/{id}')
def deletar_cliente(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.deletar_cliente(id, db, usuario)

@cliente_router.get('/listar_clientes', response_model=List[ClienteResponse])
def listar_clientes(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_clientes(db, usuario, paginacao, intervalo)

@cliente_router.get('/buscar_cliente_id/{id}', response_model=ClienteResponse)
def buscar_cliente_id(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.buscar_cliente_id(id, db, usuario)

@cliente_router.get('/buscar_cliente', response_model=List[ClienteResponse])
def buscar_cliente(
    filtro: FiltrarCliente = Depends(),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.buscar_cliente(filtro, paginacao, db, usuario)

@cliente_router.get('/buscar_clientes_por_funcionario/{usuario_id}', response_model=List[ClienteResponse])
def buscar_clientes_por_funcionario(
    usuario_id: int,
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.buscar_clientes_por_funcionario(usuario_id, db, usuario, paginacao, intervalo)
