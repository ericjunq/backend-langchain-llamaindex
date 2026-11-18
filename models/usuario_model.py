from sqlalchemy import Column, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
from utils.enums import CargosEnum

class Usuarios(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(30), nullable=False)
    sobrenome = Column(String(50), nullable=False)
    # Únicos no sistema todo: o login é por email e a conta existe antes de entrar numa empresa.
    email = Column(String(60), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    cpf = Column(String(11), nullable=False, unique=True)
    telefone = Column(String(11), nullable=False, unique=True)
    cargo = Column(SAEnum(CargosEnum), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(Boolean, default=True, nullable=False)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True, index=True)

    empresa = relationship("Empresa", back_populates='usuarios')
    clientes = relationship("Clientes", back_populates='usuario')
    vendas = relationship("Vendas", back_populates='usuario')
