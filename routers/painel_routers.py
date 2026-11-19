from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from security.dependencies import get_db
from security.security import get_current_user
import services.painel_service as service

painel_router = APIRouter(prefix='/painel', tags=['painel'])

# Visão inicial do sistema numa chamada só; o conteúdo depende do cargo (gestor vê a empresa).
@painel_router.get('')
def obter_painel(db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.montar(db, usuario)
