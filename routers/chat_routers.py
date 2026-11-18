from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from schemas.chat_schema import ChatRequest, ChatResponse
from security.dependencies import get_db
from security.security import get_current_user
import services.chat_service as service

chat_router = APIRouter(prefix='/chat', tags=['assistente'])

@chat_router.post('', response_model=ChatResponse)
def conversar(
    dados: ChatRequest,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
    fabrica=Depends(service.get_fabrica_modelo),
):
    return service.conversar(db, usuario, dados, fabrica)
