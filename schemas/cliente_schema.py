from pydantic import BaseModel, EmailStr
from security.validations import Telefone, CPF
from datetime import datetime
from typing import Optional

class ClienteCreate(BaseModel):
    nome: str
    email: EmailStr
    cpf: CPF
    telefone: Telefone

class ClienteResponse(BaseModel):
    id: int
    nome: str
    created_at: datetime
    updated_at: datetime

class ClienteUpdate(BaseModel):
    nome: Optional[str]=None
    email: Optional[EmailStr]=None
    telefone: Optional[Telefone]=None