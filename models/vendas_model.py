from sqlalchemy import Column, func, ForeignKey, String, Boolean, DateTime, Integer, Float, Numeric
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Enum as SAEnum
from utils.enums import StatusVenda, FormaPagamento


class Vendas(Base):
    __tablename__ = 'vendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    descricao = Column(String, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    valor_total = Column(Numeric(10,2), nullable=False)
    desconto = Column(Numeric(10,2), default=0, nullable=True)
    valor_final = Column(Numeric(10,2),nullable=False)
    forma_pagamento = Column(SAEnum(FormaPagamento), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    status = Column(SAEnum(StatusVenda), nullable=False, default=StatusVenda.concluida)
    motivo_cancelamento = Column(String(60), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="vendas")
    cliente = relationship("Clientes", back_populates="vendas")

class ItemVendas(Base):
    __tablename__= 'itens_vendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10,2), nullable=False)
    subtotal= Column(Numeric(10,2), nullable=False)