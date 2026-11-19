from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from schemas.chat_schema import ChatRequest, ChatResponse
from security.dependencies import get_db
from security.security import get_current_user
import services.acao_service as acao_service
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

# Executa a ação preparada pelo assistente (sem passar pelo modelo). Só o próprio usuário confirma.
@chat_router.post('/acoes/{id}/confirmar')
def confirmar_acao(id: str, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return acao_service.confirmar(db, usuario, id)

@chat_router.delete('/acoes/{id}', status_code=204)
def cancelar_acao(id: str, db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    acao_service.cancelar(db, usuario, id)
    return Response(status_code=204)
