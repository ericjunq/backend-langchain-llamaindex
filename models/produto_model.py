from sqlalchemy import Column, Index, func, UniqueConstraint, ForeignKey, String, Boolean, DateTime, Integer, Numeric
from sqlalchemy.orm import relationship
from database import Base
from utils.gerar_codigo_produto import gerar_codigo_produto

class Produtos(Base):
    __tablename__ = "produtos"

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(30), nullable=False)
    nome_normalizado = Column(String(30), nullable=False)
    codigo_produto = Column(String(13), nullable=False, default=gerar_codigo_produto)
    descricao = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_compra = Column(Numeric(10, 2), nullable=False)
    preco_venda = Column(Numeric(10, 2), nullable=False)
    estoque_min = Column(Integer, nullable=False)
    # Produto com vendas não é apagado (perderia o histórico): é desativado.
    ativo = Column(Boolean, default=True, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="produtos")
    itens_vendas = relationship("ItemVendas", back_populates="produto")

    __table_args__ = (
        UniqueConstraint('empresa_id', 'codigo_produto', name='uq_produto_codigo_empresa'),
        UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_produto_nome_empresa'),
        Index('ix_produtos_empresa_created', 'empresa_id', 'created_at'),
    )
