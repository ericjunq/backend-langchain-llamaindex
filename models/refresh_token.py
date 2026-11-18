from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Boolean
from database import Base

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(36), nullable=False, unique=True)
    token_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 em hex
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
