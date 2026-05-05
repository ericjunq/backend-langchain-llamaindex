from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from security.dependencies import get_db
from schemas.usuario_schema import UsuarioResponse, UsuarioSchema, UsuarioUpdate
from fastapi.security import OAuth2PasswordRequestForm
from schemas.convite_schema import UsarConvite
import services.usuario_service
from security.security import get_current_user

usuario_router = APIRouter(prefix="/usuario", tags=["usuario"])

@usuario_router.post('/cadastro', response_model=UsuarioResponse)
async def cadastrar_usuario(
    usuarioschema: UsuarioSchema,
    db: Session=Depends(get_db)
):
    return services.usuario_service.cadastrar_usuario(usuarioschema, db)

@usuario_router.post("/login")
async def login(
    dados: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    return services.usuario_service.login(email=dados.username, senha=dados.password, db=db)

@usuario_router.patch('/editar_usuario', response_model=UsuarioResponse)
async def editar_usuario(
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.usuario_service.editar_usuario(db, dados, usuario)

@usuario_router.patch('/vincular_empresa', response_model=UsuarioResponse)
async def vincular_empresa(
    token: UsarConvite,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.usuario_service.vincular_empresa(token, db, usuario)
