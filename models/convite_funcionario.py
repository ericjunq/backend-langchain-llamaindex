from database import Base
from sqlalchemy import DateTime, Integer, Column, func, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from datetime import timedelta, datetime, timezone

class Convite(Base):
    __tablename__ = 'convites_funcionario'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, nullable=False, unique=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, default= lambda: datetime.now(timezone.utc) + timedelta(days=1))
    usado = Column(Boolean, default=False, nullable=False)

    usuario = relationship('Usuarios', back_populates='convite_funcionario')
    empresa = relationship('Empresa', back_populates='convite_funcionario')