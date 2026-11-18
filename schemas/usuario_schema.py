from pydantic import BaseModel, Field
from typing import Optional
from security.validations import CPF, Telefone, Email
from datetime import datetime
from utils.enums import CargosEnum

class UsuarioSchema(BaseModel):
    nome: str = Field(min_length=2, max_length=30)
    sobrenome: str = Field(min_length=2, max_length=50)
    email: Email
    senha: str = Field(min_length=8, max_length=128)
    cpf: CPF
    telefone: Telefone

class UsuarioResponse(BaseModel):
    id: int
    nome: str
    cargo: Optional[CargosEnum] = None
    empresa_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class UsuarioUpdate(BaseModel):
    email: Optional[Email] = None
    senha: Optional[str] = Field(default=None, min_length=8, max_length=128)
    telefone: Optional[Telefone] = None
    # Obrigatória para trocar email ou senha (evita sequestro de conta com token roubado).
    senha_atual: Optional[str] = None

class FuncionarioFiltro(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[CPF] = None
    telefone: Optional[Telefone] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'

class RefreshRequest(BaseModel):
    refresh_token: str
