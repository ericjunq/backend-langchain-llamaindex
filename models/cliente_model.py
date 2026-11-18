from sqlalchemy import Column, Index, UniqueConstraint, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from database import Base

class Clientes(Base):
    __tablename__ = 'clientes'

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(50), nullable=False)
    # Nuláveis para permitir anonimização (LGPD) de clientes que já têm vendas.
    email = Column(String(60), nullable=True)
    telefone = Column(String(11), nullable=True)
    cpf = Column(String(11), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    status = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="clientes")
    usuario = relationship("Usuarios", back_populates="clientes")
    vendas = relationship("Vendas", back_populates="cliente")

    __table_args__ = (
        UniqueConstraint('empresa_id', 'email', name='uq_cliente_email_empresa'),
        UniqueConstraint('empresa_id', 'cpf', name='uq_cliente_cpf_empresa'),
        Index('ix_clientes_empresa_created', 'empresa_id', 'created_at'),
    )
