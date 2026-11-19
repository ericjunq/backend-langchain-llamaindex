from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from models.refresh_token import RefreshToken
from security.settings import settings
from security.security import hash_token, token_confere, criar_access_token, criar_refresh_token
from jose import jwt, JWTError
import services.auditoria_service as auditoria

TOKEN_INVALIDO = HTTPException(status_code=401, detail='Token inválido')

def emitir_tokens(usuario_id: int, db: Session) -> dict:
    """Gera access + refresh token, guarda o hash do refresh e faz o commit."""
    sub = {'sub': str(usuario_id)}  # o JWT exige 'sub' como string
    access_token = criar_access_token(data=sub)
    refresh_token, jti, expires = criar_refresh_token(data=sub)

    db.add(RefreshToken(
        jti=jti,
        token_hash=hash_token(refresh_token),
        usuario_id=usuario_id,
        expires_at=expires
    ))
    db.commit()

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer'
    }

def revogar_todos(usuario_id: int, db: Session) -> None:
    """Revoga todas as sessões ativas do usuário (sem commit)."""
    db.query(RefreshToken).filter(
        RefreshToken.usuario_id == usuario_id,
        RefreshToken.revoked.is_(False)
    ).update({'revoked': True}, synchronize_session=False)

def _validar_refresh(token: str, db: Session) -> RefreshToken:
    # jwt.decode já valida assinatura e expiração.
    try:
        payload = jwt.decode(token, settings.secret_key, [settings.algorithm])
    except JWTError:
        raise TOKEN_INVALIDO

    if payload.get('token_type') != 'refresh' or not payload.get('sub') or not payload.get('jti'):
        raise TOKEN_INVALIDO

    token_db = db.query(RefreshToken).filter(RefreshToken.jti == payload['jti']).first()
    if token_db is None or not token_confere(token, token_db.token_hash):
        raise TOKEN_INVALIDO

    return token_db

def refresh(token: str, db: Session) -> dict:
    token_db = _validar_refresh(token, db)

    # Conta desativada/anonimizada: só recusa (sem "detecção de reuso" nem alerta por email).
    usuario = db.get(Usuarios, token_db.usuario_id)
    if usuario is None or not usuario.status:
        raise TOKEN_INVALIDO

    # Detecção de reuso: um refresh já usado voltou → possível roubo. Derruba todas as sessões.
    if token_db.revoked:
        revogar_todos(usuario.id, db)
        auditoria.registrar(db, 'token.reuso_detectado', usuario=usuario, categoria=auditoria.ACESSO)
        db.commit()
        import services.email_service as email_service
        email_service.avisar_sessao_comprometida(usuario.nome, usuario.email)
        raise HTTPException(status_code=401, detail='Sessão comprometida, faça o login novamente')

    token_db.revoked = True
    return emitir_tokens(usuario.id, db)  # um único commit: revogação + novo token

def logout(token: str, db: Session) -> dict:
    token_db = _validar_refresh(token, db)
    token_db.revoked = True
    db.commit()
    return {'message': 'Logout realizado com sucesso'}

def logout_geral(token: str, db: Session) -> dict:
    token_db = _validar_refresh(token, db)
    if token_db.revoked:
        raise TOKEN_INVALIDO

    revogar_todos(token_db.usuario_id, db)
    auditoria.registrar(db, 'logout_geral', usuario=db.get(Usuarios, token_db.usuario_id), categoria=auditoria.ACESSO)
    db.commit()
    return {'message': 'Todas as sessões foram encerradas'}
