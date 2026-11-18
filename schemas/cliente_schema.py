from pydantic import BaseModel, Field
from security.validations import Telefone, CPF, Email
from datetime import datetime
from typing import Optional

class ClienteCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=50)
    email: Email
    cpf: CPF
    telefone: Telefone

# Mínima exposição (LGPD): listagens devolvem só id e nome.
class ClienteResponse(BaseModel):
    id: int
    nome: str
    created_at: datetime
    updated_at: datetime

class ClienteUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=50)
    email: Optional[Email] = None
    telefone: Optional[Telefone] = None

class FiltrarCliente(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[CPF] = None
    telefone: Optional[Telefone] = None
