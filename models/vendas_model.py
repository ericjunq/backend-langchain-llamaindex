from sqlalchemy import Column, Index, func, ForeignKey, String, DateTime, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
from utils.enums import StatusVenda, FormaPagamento


class Vendas(Base):
    __tablename__ = 'vendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    descricao = Column(String, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False, index=True)
    valor_total = Column(Numeric(10, 2), nullable=False)
    desconto = Column(Numeric(10, 2), default=0, nullable=False)
    valor_final = Column(Numeric(10, 2), nullable=False)
    forma_pagamento = Column(SAEnum(FormaPagamento), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    status = Column(SAEnum(StatusVenda), nullable=False, default=StatusVenda.concluida)
    motivo_cancelamento = Column(String(60), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="vendas")
    cliente = relationship("Clientes", back_populates="vendas")
    usuario = relationship("Usuarios", back_populates="vendas")
    itens = relationship("ItemVendas", back_populates='venda', cascade='all, delete-orphan')

    __table_args__ = (
        # Listagens e relatórios filtram por empresa + data: índice composto cobre os dois.
        Index('ix_vendas_empresa_created', 'empresa_id', 'created_at'),
    )

class ItemVendas(Base):
    __tablename__ = 'itens_vendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    # Preço de compra no momento da venda: a margem continua correta se o custo do produto mudar depois.
    custo_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    venda = relationship('Vendas', back_populates='itens')
    produto = relationship('Produtos', back_populates='itens_vendas')
