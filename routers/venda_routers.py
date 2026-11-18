from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.venda_schema import VendaResponse, VendaSchema, CancelarVenda
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
from utils.data_filter import IntervaloData, get_intervalo_data
from utils.paginacao import Paginacao, get_paginacao
import services.venda_service as service

venda_router = APIRouter(prefix='/vendas', tags=['vendas'])

@venda_router.post('/criar_venda', response_model=VendaResponse, status_code=201)
def criar_venda(
    vendaschema: VendaSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_venda(vendaschema, db, usuario)

@venda_router.patch('/cancelar_venda/{id}', response_model=VendaResponse)
def cancelar_venda(
    id: int,
    cancelamento: CancelarVenda,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.cancelar_venda(id, cancelamento, db, usuario)

@venda_router.get('/listar_vendas', response_model=List[VendaResponse])
def listar_vendas(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.listar_vendas(db, usuario, paginacao, intervalo)

@venda_router.get('/listar_vendas_funcionario/{id}', response_model=List[VendaResponse])
def listar_vendas_funcionario(
    id: int,
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.listar_vendas_funcionario(id, db, usuario, paginacao, intervalo)
