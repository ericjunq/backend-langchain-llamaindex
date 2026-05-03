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

refresh_token_router = APIRouter(prefix='/refresh_token', tags=['refresh token'])
oauth_scheme = OAuth2PasswordBearer(tokenUrl='/login')

@refresh_token_router.post('/refresh')
async def refresh(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            [settings.algorithm]
        )

        if payload.get('token_type') != 'refresh':
            raise HTTPException(status_code=401, detail='Token inválido')

        user_id = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=401, detail='Token inválido')
        
        usuario = db.query(Usuarios).filter(
            Usuarios.id == user_id
        ).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail='Usuário não encontrado')
        
        if payload.get('jti') is None:
            raise HTTPException(status_code=401, detail='Token inválido')
    
        token_db = db.query(RefreshToken).filter(
            RefreshToken.jti == payload.get('jti')
        ).first()
        if token_db is None:
            raise HTTPException(status_code=401, detail='Token inválido')
        
        # Reuse Detection
        if token_db.revoked:
            db.query(RefreshToken).filter(
                RefreshToken.usuario_id == user_id,
                RefreshToken.revoked.is_(False)
            ).update({'revoked': True})

            db.commit()

            raise HTTPException(status_code=401, detail='Sessão comprometida, faça o login novamente')

        if not verificar_senha(token, token_db.token_hash):
            raise HTTPException(status_code=401, detail='Token inválido')
        
        agora = datetime.now(timezone.utc)
        if payload.get('exp') <= agora.timestamp():
            raise HTTPException(status_code=400, detail='Token expirado')
    
        if token_db.expires_at <= agora:
            raise HTTPException(status_code=400, detail='Token expirado')

    except JWTError:
        raise HTTPException(status_code=401, detail='Token inválido')
    
    token_db.revoked = True
    db.commit()
    
    novo_access_token = criar_access_token(
        data={'sub': user_id}
    )

    novo_refresh_token, novo_jti, expires = criar_refresh_token(
        data={'sub': user_id}
    )

    refresh_token = RefreshToken(
        jti=novo_jti,
        token_hash=criptografar_senha(novo_refresh_token),
        usuario_id = user_id,
        expires_at=expires
    )

    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    db.refresh(token_db)

    
    return {
        'access_token':novo_access_token,
        'refresh_token':novo_refresh_token,
        'token_type':'bearer'
    }

@refresh_token_router.post('/logout')
async def logout(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            [settings.algorithm]
        )

        if payload.get('token_type') != 'refresh':
            raise HTTPException(status_code=401, detail='Token inválido')

        jti = payload.get('jti')
        if jti is None:
            raise HTTPException(status_code=401, detail='Token inválido')
        
        token_db = db.query(RefreshToken).filter(
            RefreshToken.jti == jti
        ).first()

        if token_db is None:
            raise HTTPException(status_code=401, detail='Token inválido')

        if not verificar_senha(token, token_db.token_hash):
            raise HTTPException(status_code=401, detail='Token inválido')

        token_db.revoked = True
        db.commit()

    except JWTError:
        raise HTTPException(status_code=401, detail='Token inválido')
    
    return {'message': 'Logout realizado com sucesso'}

@refresh_token_router.post('/logout_geral')
async def logout_geral(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            [settings.algorithm]
        )

        if payload.get('token_type') != 'refresh':
            raise HTTPException(status_code=401, detail='Token inválido')

        user_id = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=401, detail='Token inválido')
        
        if payload.get('jti') is None:
            raise HTTPException(status_code=401, detail='Token inválido')
        
        token_db = db.query(RefreshToken).filter(
            RefreshToken.jti == payload.get('jti')
        ).first()
        if token_db is None:
            raise HTTPException(status_code=401, detail='Token inválido')
        
        if not verificar_senha(token, token_db.token_hash):
            raise HTTPException(status_code=401, detail='Token inválido')
        
        db.query(RefreshToken).filter(
            RefreshToken.usuario_id == user_id,
            RefreshToken.revoked.is_(False)
        ).update({'revoked': True})
        
        db.commit()
    
    except JWTError:
        raise HTTPException(status_code=401,detail='Token inválido')
    
    return {'message': 'Todas as sessões foram deslogadas'}
        