from pydantic import BaseModel, Field
from typing import Annotated, Optional
from datetime import datetime
from decimal import Decimal

Preco = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]

class ProdutoSchema(BaseModel):
    nome: str = Field(min_length=1, max_length=30)
    descricao: str = Field(min_length=1, max_length=500)
    quantidade: int = Field(ge=0)
    preco_compra: Preco
    preco_venda: Preco
    estoque_min: int = Field(ge=0)

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    codigo_produto: str
    descricao: str
    quantidade: int
    preco_compra: Decimal
    preco_venda: Decimal
    estoque_min: int
    created_at: datetime
    updated_at: datetime

class ProdutoUpdate(BaseModel):
    descricao: Optional[str] = Field(default=None, min_length=1, max_length=500)
    preco_compra: Optional[Preco] = None
    preco_venda: Optional[Preco] = None
    estoque_min: Optional[int] = Field(default=None, ge=0)

class ProdutoReposicaoEstoque(BaseModel):
    quantidade: int = Field(gt=0)

class FiltrarProdutos(BaseModel):
    nome: Optional[str] = None
    codigo_produto: Optional[str] = None
    preco_compra: Optional[Decimal] = None
    preco_venda: Optional[Decimal] = None
    estoque_min: Optional[int] = None
    abaixo_estoque_min: bool = Field(default=False, description='Só produtos com quantidade <= estoque mínimo')
