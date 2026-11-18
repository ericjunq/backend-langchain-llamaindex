from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.venda_schema import VendaResponse, VendaSchema, CancelarVenda, FiltroVendas
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
from utils.data_filter import IntervaloData, get_intervalo_data
from utils.paginacao import Paginacao, get_paginacao
import services.venda_service as service

venda_router = APIRouter(prefix='/vendas', tags=['vendas'])

@venda_router.post('', response_model=VendaResponse, status_code=201)
def criar_venda(
    dados: VendaSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_venda(dados, db, usuario)

@venda_router.get('', response_model=List[VendaResponse])
def listar_vendas(
    filtro: FiltroVendas = Depends(),
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.listar_vendas(filtro, db, usuario, paginacao, intervalo)

@venda_router.get('/{id}', response_model=VendaResponse)
def obter_venda(id: int, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.obter_venda(id, db, usuario)

# Venda não é editada nem apagada (histórico financeiro): só cancelada, com motivo.
@venda_router.post('/{id}/cancelar', response_model=VendaResponse)
def cancelar_venda(
    id: int,
    dados: CancelarVenda,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.cancelar_venda(id, dados, db, usuario)
