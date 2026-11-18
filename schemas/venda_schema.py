from pydantic import BaseModel, Field
from datetime import datetime
from utils.enums import FormaPagamento, StatusVenda
from decimal import Decimal
from typing import Optional, List

class ItemVendaSchema(BaseModel):
    produto_id: int
    quantidade: int = Field(gt=0)

class VendaSchema(BaseModel):
    descricao: str = Field(min_length=1, max_length=255)
    cliente_id: Optional[int] = None
    itens: List[ItemVendaSchema] = Field(min_length=1)
    # valor_total e valor_final são calculados no servidor a partir do preço do produto.
    desconto: Decimal = Field(default=Decimal('0'), ge=0, max_digits=10, decimal_places=2)
    forma_pagamento: FormaPagamento

class ItemVendaResponse(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    subtotal: Decimal

class VendaResponse(BaseModel):
    id: int
    descricao: str
    cliente_id: Optional[int] = None
    usuario_id: int
    itens: List[ItemVendaResponse]
    valor_total: Decimal
    desconto: Decimal
    valor_final: Decimal
    forma_pagamento: FormaPagamento
    empresa_id: int
    status: StatusVenda
    motivo_cancelamento: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CancelarVenda(BaseModel):
    motivo_cancelamento: str = Field(min_length=3, max_length=60)
