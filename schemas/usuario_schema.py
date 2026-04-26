from pydantic import BaseModel, EmailStr
from typing import Optional
from security.validations import CPF, Telefone
from datetime import datetime

class UsuarioSchema(BaseModel):
    nome: str 
    sobrenome: str
    email: EmailStr
    senha: str
    cpf: CPF
    telefone: Telefone

class UsuarioResponse(BaseModel):
    id: int
    nome: str
    created_at: datetime
    updated_at: datetime

class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    telefone: Optional[Telefone] = None
