from pydantic import BaseModel, EmailStr
from typing import Optional
from security.validations import CNPJ, Telefone
from datetime import datetime

class EmpresaCreate(BaseModel):
    nome: str
    cnpj: CNPJ
    email: EmailStr
    telefone: Telefone

class EmpresaResponse(BaseModel):
    id: int
    nome: str
    cnpj: CNPJ
    created_at: datetime
    updated_at: datetime

class EmpresaUpdate(BaseModel):
    email: Optional[EmailStr]
    telefone: Optional[Telefone]