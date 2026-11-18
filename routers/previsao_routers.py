from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
import services.previsao_service as service

previsao_router = APIRouter(prefix='/previsoes', tags=['previsões'])

@previsao_router.get('/produtos/{id}')
def prever_produto(
    id: int,
    dias: int = Query(30, ge=1, le=180, description='Horizonte da previsão, em dias'),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.prever_produto(db, usuario, id, dias)

@previsao_router.get('/reposicao')
def sugerir_reposicao(
    prazo_entrega: int = Query(7, ge=0, le=90, description='Dias até o fornecedor entregar'),
    dias_cobertura: int = Query(30, ge=1, le=180, description='Por quantos dias a compra deve durar após chegar'),
    apenas_necessarios: bool = Query(True, description='Só produtos com compra sugerida > 0'),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.sugerir_reposicao(db, usuario, prazo_entrega, dias_cobertura, apenas_necessarios)
