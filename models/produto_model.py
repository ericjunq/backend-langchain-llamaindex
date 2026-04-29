from sqlalchemy import Column, func, UniqueConstraint, ForeignKey, String, Boolean, DateTime, Integer, Float
from sqlalchemy.orm import relationship
from database import Base
from utils.gerar_codigo_produto import gerar_codigo_produto
from sqlalchemy.dialects.postgresql import UUID

class Produtos(Base):
    __tablename__ = "produtos"

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(30), nullable=False)
    nome_normalizado = Column(String(30), index=True, nullable=False)
    codigo_produto = Column(UUID(as_uuid=True),  index=True, default=gerar_codigo_produto)
    descricao = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_compra = Column(Float, nullable=False)
    preco_venda = Column(Float, nullable=False)
    estoque_min = Column(Integer, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="produtos")

    __table_args__ = (
        UniqueConstraint('empresa_id', 'codigo_produto', name='uq_produto_codigo_empresa'),
        UniqueConstraint("nome_normalizado", "empresa_id", name="uq_produto_nome_empresa")
    )
