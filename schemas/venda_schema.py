from pydantic import BaseModel
from datetime import datetime
from utils.enums import FormaPagamento, StatusVenda
from decimal import Decimal
from typing import Optional, List

class ItemVendaSchema(BaseModel):
    produto_id: int
    quantidade: int

class VendaSchema(BaseModel):
    descricao: str
    cliente_id: Optional[int]=None
    itens : List[ItemVendaSchema]
    valor_total: Decimal
    desconto: Decimal
    valor_final: Decimal
    forma_pagamento: FormaPagamento


class VendaReponse(BaseModel):
    id: int
    descricao: str
    cliente_id: int
    usuario_id: int
    itens : List[ItemVendaSchema]
    valor_total: Decimal
    desconto: Decimal
    valor_final: Decimal
    empresa_id: int
    status: StatusVenda
    motivo_cancelamento: str
    created_at: datetime
    updated_at: datetime

class CancelarVenda(BaseModel):
    motivo_cancelamento: str