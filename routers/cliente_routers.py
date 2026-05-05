from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.cliente_schema import FiltrarCliente, ClienteCreate, ClienteResponse, ClienteUpdate
from security.dependencies import get_db
from models.usuario_model import Usuarios
from security.security import get_current_user
from typing import List, Optional
from schemas.filtrodata_schema import DataFilter, Periodo
from utils.data_filter import get_data_filter
import services.cliente_service

cliente_router = APIRouter(prefix='/cliente', tags=['clientes'])

@cliente_router.post('/adicionar_cliente', response_model=ClienteResponse)
async def adicionar_cliente(
    clienteschema: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.adicionar_cliente(clienteschema, db, usuario)

@cliente_router.patch('/editar_cliente/{id}', response_model=ClienteResponse)
async def editar_cliente(
    id: int,
    dados: ClienteUpdate,
    db: Session=Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.editar_cliente(id, dados,db,usuario)

@cliente_router.delete('/deletar_cliente/{id}')
async def deletar_cliente(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.deletar_cliente(id, db, usuario)

@cliente_router.get('/listar_clientes', response_model=List[ClienteResponse])
async def listar_clientes(
    periodo: Optional[Periodo] = None,
    datafilter: DataFilter = Depends(get_data_filter),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.listar_clientes(db, usuario, periodo=periodo, datafilter=datafilter)

@cliente_router.get('/buscar_cliente_id/{id}', response_model=ClienteResponse)
async def buscar_cliente_id(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.buscar_cliente_id(id, db, usuario)

@cliente_router.get('/buscar_cliente', response_model=List[ClienteResponse])
async def buscar_cliente(
    filtro: FiltrarCliente = Depends(),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.buscar_cliente(filtro, db, usuario)

@cliente_router.get('/buscar_clientes_por_funcionario/{usuario_id}', response_model=List[ClienteResponse])
async def buscar_clientes_por_funcionario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.cliente_service.buscar_clientes_por_funcionario(usuario_id, db, usuario)