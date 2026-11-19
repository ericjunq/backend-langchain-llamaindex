"""Sessão (não é CRUD).

O refresh token vive num cookie httpOnly (o JavaScript do navegador não consegue lê-lo, então
um ataque XSS não o rouba). O corpo das respostas traz só o access token, que o frontend guarda
em memória. Cookie: Secure, SameSite=Strict (não vai em requisições vindas de outros sites →
proteção contra CSRF) e Path restrito a /api/v1/auth (só as rotas de sessão o recebem).
"""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from schemas.usuario_schema import TokenResponse
from security.dependencies import get_db
from security.settings import settings
from utils.versao_api import API_V1
import services.refresh_token_service as token_service
import services.usuario_service as usuario_service

auth_router = APIRouter(prefix='/auth', tags=['auth'])

COOKIE_SESSAO = 'refresh_token'
CAMINHO_COOKIE = f'{API_V1}/auth'


def _gravar_sessao(resposta: Response, tokens: dict) -> dict:
    resposta.set_cookie(
        COOKIE_SESSAO, tokens['refresh_token'],
        max_age=settings.refresh_token_expires_days * 86400,
        httponly=True, secure=settings.cookie_secure, samesite='strict', path=CAMINHO_COOKIE,
    )
    return {
        'access_token': tokens['access_token'],
        'token_type': 'bearer',
        'expires_in': settings.access_token_expires_minutes * 60,  # para o frontend renovar antes de vencer
    }


def _apagar_sessao(resposta: Response) -> None:
    resposta.delete_cookie(COOKIE_SESSAO, path=CAMINHO_COOKIE, httponly=True,
                           secure=settings.cookie_secure, samesite='strict')


def _cookie_obrigatorio(refresh_token: Optional[str] = Cookie(None)) -> str:
    if not refresh_token:
        raise HTTPException(status_code=401, detail='Sessão expirada: faça o login novamente')
    return refresh_token


@auth_router.post('/login', response_model=TokenResponse)
def login(request: Request, resposta: Response, dados: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    ip = request.client.host if request.client else 'desconhecido'
    tokens = usuario_service.login(email=dados.username, senha=dados.password, db=db, ip=ip)
    return _gravar_sessao(resposta, tokens)


@auth_router.post('/refresh', response_model=TokenResponse)
def refresh(resposta: Response, token: str = Depends(_cookie_obrigatorio), db: Session = Depends(get_db)):
    return _gravar_sessao(resposta, token_service.refresh(token, db))


@auth_router.post('/logout')
def logout(resposta: Response, refresh_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    # Idempotente: sem cookie ou com cookie inválido, só garante que o cookie some do navegador.
    if refresh_token:
        try:
            token_service.logout(refresh_token, db)
        except HTTPException:
            pass
    _apagar_sessao(resposta)
    return {'message': 'Logout realizado com sucesso'}


@auth_router.post('/logout-geral')
def logout_geral(resposta: Response, token: str = Depends(_cookie_obrigatorio), db: Session = Depends(get_db)):
    resultado = token_service.logout_geral(token, db)
    _apagar_sessao(resposta)
    return resultado
