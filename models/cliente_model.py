from sqlalchemy import Column, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from database import Base

class Clientes(Base):
    __tablename__ = 'clientes'

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(50), nullable=False)
    email = Column(String(50), nullable=False)
    telefone = Column(String(11), nullable=False)
    observacao = Column(String, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    status = Column(Boolean, default=True, nullable=False)

    empresa = relationship("Empresa", back_populates="clientes")
    usuario = relationship("Usuarios", back_populates="cliente")
    vendas = relationship("Vendas", back_populates="cliente")