from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from models.refresh_token import RefreshToken
from security.dependencies import get_db
from security.settings import settings
from security.security import criptografar_senha, verificar_senha, criar_access_token, criar_refresh_token
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timezone
import services.refresh_token_service

refresh_token_router = APIRouter(prefix='/refresh_token', tags=['refresh token'])
oauth_scheme = OAuth2PasswordBearer(tokenUrl='/login')

@refresh_token_router.post('/refresh')
async def refresh(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db),
):
    return services.refresh_token_service.refresh(token, db)

@refresh_token_router.post('/logout')
async def logout(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db)
):
    return services.refresh_token_service.logout(token, db)

@refresh_token_router.post('/logout_geral')
async def logout_geral(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db)
):
    return services.refresh_token_service.logout_geral(token, db)