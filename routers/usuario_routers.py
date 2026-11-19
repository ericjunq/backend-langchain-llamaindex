from fastapi import Depends, APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from security.dependencies import get_db
from security.security import get_current_user
from schemas.usuario_schema import UsuarioResponse, UsuarioSchema, UsuarioUpdate
from schemas.convite_schema import UsarConvite
import services.usuario_service as service

usuario_router = APIRouter(prefix="/usuarios", tags=["usuários"])
convite_router = APIRouter(prefix="/convites", tags=["usuários"])

@usuario_router.post('', response_model=UsuarioResponse, status_code=201)
def cadastrar_usuario(dados: UsuarioSchema, db: Session = Depends(get_db)):
    return service.cadastrar_usuario(dados, db)

@usuario_router.get('/me', response_model=UsuarioResponse)
def meu_usuario(usuario: Usuarios = Depends(get_current_user)):
    return usuario

# Direito de acesso do titular (LGPD). Sem cache: a resposta tem CPF, email e telefone.
@usuario_router.get('/me/dados')
def exportar_meus_dados(db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    dados = jsonable_encoder(service.exportar_meus_dados(db, usuario))
    return JSONResponse(dados, headers={'Cache-Control': 'no-store'})

@usuario_router.patch('/me', response_model=UsuarioResponse)
def editar_usuario(
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_usuario(db, dados, usuario)

# O token do convite vai no corpo, não na URL: é um segredo e não deve parar em logs.
@convite_router.post('/aceitar', response_model=UsuarioResponse)
def aceitar_convite(
    dados: UsarConvite,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.vincular_empresa(dados, db, usuario)
