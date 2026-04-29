from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProdutoSchema(BaseModel):
    nome: str
    descricao: str
    quantidade: int
    preco_compra: float
    preco_venda: float
    estoque_min: int

class ProdutoReponse(BaseModel):
    id: int
    nome: str
    descricao: str
    quantidade: int
    preco_compra: float
    preco_venda: float
    estoque_min: int
    created_at: datetime
    created_at: datetime

class ProdutoUpdate(BaseModel):
    descricao: Optional[str]=None
    preco_compra: Optional[float]=None
    preco_venda: Optional[float]=None
    estoque_min: Optional[int]=None

class ProdutoReposicaoEstoque(BaseModel):
    quantidade: int

class FiltrarProdutos(BaseModel):
    nome: Optional[str]=None
    nome_normalizado: Optional[str]=None
    codigo_produto: Optional[str]=None
    preco_compra: Optional[float]=None
    preco_venda: Optional[float]=None
    estoque_min: Optional[int]=None