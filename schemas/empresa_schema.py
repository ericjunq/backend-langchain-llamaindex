from pydantic import BaseModel, Field
from typing import Optional
from security.validations import CNPJ, Telefone, Email
from datetime import datetime
from utils.enums import CargosFuncionarios

class EmpresaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=40)
    cnpj: CNPJ
    email: Email
    telefone: Telefone

class EmpresaResponse(BaseModel):
    id: int
    nome: str
    cnpj: str
    created_at: datetime
    updated_at: datetime

class EmpresaUpdate(BaseModel):
    email: Optional[Email] = None
    telefone: Optional[Telefone] = None

class CargoUpdate(BaseModel):
    cargo: CargosFuncionarios
