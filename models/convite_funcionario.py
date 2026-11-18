from database import Base
from sqlalchemy import DateTime, Integer, Column, func, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from datetime import timedelta, datetime, timezone

def _expiracao_padrao() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=1)

class Convite(Base):
    __tablename__ = 'convites_funcionario'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(64), nullable=False, unique=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, default=_expiracao_padrao, index=True)
    usado = Column(Boolean, default=False, nullable=False)

    usuario = relationship('Usuarios')
    empresa = relationship('Empresa', back_populates='convites')
