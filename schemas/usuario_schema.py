from pydantic import BaseModel, EmailStr
from typing import Optional
from security.validations import CPF, Telefone
from datetime import datetime
from utils.enums import CargosEnum

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
    cargo: Optional[CargosEnum]=None
    empresa_id: int
    created_at: datetime
    updated_at: datetime

class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    telefone: Optional[Telefone] = None

class FuncionarioFiltro(BaseModel):
    nome: Optional[str]=None
    sobrenome: Optional[str]
    email: Optional[EmailStr]
    cpf: Optional[CPF]
    telefone: Optional[Telefone]