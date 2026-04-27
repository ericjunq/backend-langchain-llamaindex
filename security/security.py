from pwdlib import PasswordHash
from datetime import datetime, timedelta,timezone
from jose import JWTError, jwt
from security.settings import settings
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from security.dependencies import get_db
from models.usuario_model import Usuarios

password_hash = PasswordHash.recommended()

usuario_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login_usuario')

def criptografar_senha(senha: str) -> str:
    return password_hash.hash(senha)

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)

def criar_access_token(data: dict)-> str:
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expires_minutes)
    to_encode.update({'exp': expires})

    access_token = jwt.encode(
        to_encode,
        settings.secret_key,
        settings.algorithm
    )

    return access_token

def criar_refresh_token(data:dict)->str:
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expires_days)
    to_encode.update({'exp': expires})

    refresh_token = jwt.encode(
        to_encode,
        settings.secret_key,
        settings.algorithm
    )
    
    return refresh_token

def get_current_user(
        token: str = Depends(usuario_scheme), 
        db: Session = Depends(get_db)
    ):

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            [settings.algorithm]
        )
        email = payload.get('sub')
        if email is None:
            raise HTTPException(status_code=401, detail='Token inválido')
    except JWTError:
        raise HTTPException(status_code=401, detail='Token inválido')
    
    usuario = db.query(Usuarios).filter(
        Usuarios.email == email
    ).first()

    if usuario is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    
    return usuario