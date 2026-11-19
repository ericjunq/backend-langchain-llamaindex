from fastapi import Depends, APIRouter, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from schemas.usuario_schema import RefreshRequest, TokenResponse
from security.dependencies import get_db
import services.usuario_service as usuario_service
import services.refresh_token_service as token_service

# Sessão (não é CRUD): ações sobre tokens. O refresh token vai no corpo (JSON),
# não no header Authorization, para não se confundir com o access token.
auth_router = APIRouter(prefix='/auth', tags=['auth'])

@auth_router.post('/login', response_model=TokenResponse)
def login(request: Request, dados: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else 'desconhecido'
    return usuario_service.login(email=dados.username, senha=dados.password, db=db, ip=ip)

@auth_router.post('/refresh', response_model=TokenResponse)
def refresh(dados: RefreshRequest, db: Session = Depends(get_db)):
    return token_service.refresh(dados.refresh_token, db)

@auth_router.post('/logout')
def logout(dados: RefreshRequest, db: Session = Depends(get_db)):
    return token_service.logout(dados.refresh_token, db)

@auth_router.post('/logout-geral')
def logout_geral(dados: RefreshRequest, db: Session = Depends(get_db)):
    return token_service.logout_geral(dados.refresh_token, db)
