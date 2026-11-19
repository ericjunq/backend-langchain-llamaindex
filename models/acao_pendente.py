from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func
from database import Base

VALIDADE_MINUTOS = 10

def _expiracao() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=VALIDADE_MINUTOS)

class AcaoPendente(Base):
    """Ação de escrita proposta pelo assistente. Só é executada quando o próprio usuário confirma
    (rota de confirmação, sem passar pelo modelo). Expira em poucos minutos e é apagada (retenção)."""
    __tablename__ = 'acoes_pendentes'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    tipo = Column(String(30), nullable=False)
    dados = Column(JSON, nullable=False)       # só ids e quantidades (nada pessoal)
    resumo = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, default=_expiracao, index=True)
