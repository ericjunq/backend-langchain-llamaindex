from sqlalchemy import Column, UniqueConstraint, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from database import Base

class Clientes(Base):
    __tablename__ = 'clientes'

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(50), nullable=False)
    email = Column(String(50), nullable=False)
    telefone = Column(String(11), nullable=False)
    cpf = Column(String(11), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    status = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="clientes")
    usuario = relationship("Usuarios", back_populates="cliente")
    vendas = relationship("Vendas", back_populates="cliente")

    __table_args__ = (
        UniqueConstraint('empresa_id', 'email', name='uq_cliente_email_empresa'),
        UniqueConstraint('empresa_id', 'cpf', name='uq_cliente_cpf_empresa')
    )