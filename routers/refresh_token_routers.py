from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from schemas.usuario_schema import RefreshRequest, TokenResponse
from security.dependencies import get_db
import services.refresh_token_service as service

# O refresh token vai no corpo (JSON), não no header Authorization:
# assim ele não se confunde com o access token no Swagger nem no frontend.
refresh_token_router = APIRouter(prefix='/refresh_token', tags=['refresh token'])

@refresh_token_router.post('/refresh', response_model=TokenResponse)
def refresh(dados: RefreshRequest, db: Session = Depends(get_db)):
    return service.refresh(dados.refresh_token, db)

@refresh_token_router.post('/logout')
def logout(dados: RefreshRequest, db: Session = Depends(get_db)):
    return service.logout(dados.refresh_token, db)

@refresh_token_router.post('/logout_geral')
def logout_geral(dados: RefreshRequest, db: Session = Depends(get_db)):
    return service.logout_geral(dados.refresh_token, db)
