from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from schemas.auditoria_schema import FiltroAuditoria
from security.dependencies import get_db
from security.security import get_current_user
from utils.data_filter import IntervaloData, get_intervalo_data
from utils.paginacao import Paginacao, get_paginacao
import services.auditoria_service as service

auditoria_router = APIRouter(prefix='/auditoria', tags=['auditoria'])

# Só leitura (e só o dono): a trilha não tem rota de edição nem de exclusão.
@auditoria_router.get('')
def listar_auditoria(
    filtro: FiltroAuditoria = Depends(),
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.listar(db, usuario, filtro, paginacao, intervalo)
