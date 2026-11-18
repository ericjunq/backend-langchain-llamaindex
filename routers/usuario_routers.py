from fastapi import Depends, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from security.dependencies import get_db
from security.security import get_current_user
from schemas.usuario_schema import UsuarioResponse, UsuarioSchema, UsuarioUpdate, TokenResponse
from schemas.convite_schema import UsarConvite
import services.usuario_service as service

usuario_router = APIRouter(prefix="/usuario", tags=["usuario"])

@usuario_router.post('/cadastro', response_model=UsuarioResponse, status_code=201)
def cadastrar_usuario(
    usuarioschema: UsuarioSchema,
    db: Session = Depends(get_db)
):
    return service.cadastrar_usuario(usuarioschema, db)

@usuario_router.post("/login", response_model=TokenResponse)
def login(
    dados: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    return service.login(email=dados.username, senha=dados.password, db=db)

@usuario_router.get('/me', response_model=UsuarioResponse)
def meu_usuario(usuario: Usuarios = Depends(get_current_user)):
    return usuario

@usuario_router.patch('/editar_usuario', response_model=UsuarioResponse)
def editar_usuario(
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_usuario(db, dados, usuario)

@usuario_router.patch('/vincular_empresa', response_model=UsuarioResponse)
def vincular_empresa(
    token: UsarConvite,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.vincular_empresa(token, db, usuario)
