from sqlalchemy import Column, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from database import Base

class Empresa(Base):
    __tablename__ = 'empresas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(40), nullable=False)
    cnpj = Column(String(14), unique=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    telefone = Column(String(11), unique=True, nullable=False)
    status = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuarios = relationship("Usuarios", back_populates="empresa")
    clientes = relationship("Clientes" ,back_populates="empresa")
    vendas = relationship("Vendas", back_populates="empresa")
    produtos = relationship("Produtos", back_populates="empresa")