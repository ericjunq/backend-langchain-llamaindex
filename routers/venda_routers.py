from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.venda_schema import VendaReponse, VendaSchema, CancelarVenda
from security.dependencies import get_db
from models.usuario_model import Usuarios
from security.security import get_current_user
import services.venda_service
from typing import List,Optional
from schemas.filtrodata_schema import Periodo, DataFilter

venda_router = APIRouter(prefix='/vendas', tags=['vendas'])

@venda_router.post('/criar_venda', response_model=VendaReponse)
async def criar_venda(
    vendaschema: VendaSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.venda_service.criar_venda(vendaschema, db, usuario)

@venda_router.patch('/cancelar_venda/{id}', response_model=VendaReponse)
async def cancelar_venda(
    id: int,
    cancelamento: CancelarVenda,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.venda_service.cancelar_venda(id, cancelamento, db, usuario)

@venda_router.get('/listar_vendas', response_model=List[VendaReponse])
async def listar_vendas(
    db: Session=Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
    periodo : Optional[Periodo]=None,
    datafilter: Optional[DataFilter]=None
):
    return services.venda_service.listar_vendas(db, usuario, periodo, datafilter)

@venda_router.get('/listar_vendas_funcionario/{id}', response_model=List[VendaReponse])
async def listar_vendas_funcionario(
    id: int,
    db: Session=Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
    periodo : Optional[Periodo]=None,
    datafilter: Optional[DataFilter]=None
):
    return services.venda_service.listar_vendas_funcionario(id, db, usuario, periodo, datafilter)