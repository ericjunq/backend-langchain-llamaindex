from sqlalchemy import Column, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from database import Base


class Vendas(Base):
    __tablename__ = 'vendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    descricao = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    empresa = relationship("Empresa", back_populates="vendas")
    cliente = relationship("Clientes", back_populates="vendas")
