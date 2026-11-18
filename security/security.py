import hashlib
import hmac
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from security.settings import settings
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from security.dependencies import get_db
from models.usuario_model import Usuarios
from uuid import uuid4

password_hash = PasswordHash.recommended()

usuario_scheme = OAuth2PasswordBearer(tokenUrl='/usuario/login')

# Hash usado no login quando o email não existe: assim a resposta leva o mesmo
# tempo nos dois casos e não dá para descobrir quais emails estão cadastrados (LGPD).
HASH_FALSO = password_hash.hash('senha-inexistente-para-tempo-constante')

# --- Senhas (Argon2: lento de propósito, contra força bruta) ---

def criptografar_senha(senha: str) -> str:
    return password_hash.hash(senha)

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)

# --- Refresh tokens (SHA-256: o token já é aleatório e longo, não precisa de Argon2) ---

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def token_confere(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), token_hash)

# --- JWT ---

def criar_access_token(data: dict) -> str:
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expires_minutes)
    to_encode.update({
        'exp': expires,
        'token_type': 'access'
    })
    return jwt.encode(to_encode, settings.secret_key, settings.algorithm)

def criar_refresh_token(data: dict):
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expires_days)
    jti = str(uuid4())
    to_encode.update({
        'jti': jti,
        'exp': expires,
        'token_type': 'refresh'
    })
    refresh_token = jwt.encode(to_encode, settings.secret_key, settings.algorithm)
    return refresh_token, jti, expires

def get_current_user(
        token: str = Depends(usuario_scheme),
        db: Session = Depends(get_db)
    ) -> Usuarios:
    erro = HTTPException(status_code=401, detail='Token inválido', headers={'WWW-Authenticate': 'Bearer'})

    try:
        payload = jwt.decode(token, settings.secret_key, [settings.algorithm])
    except JWTError:
        raise erro

    sub = payload.get('sub')
    if sub is None or payload.get('token_type') != 'access':
        raise erro

    usuario = db.get(Usuarios, int(sub))
    if usuario is None or not usuario.status:
        raise erro

    return usuario
