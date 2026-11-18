from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.empresa_schema import EmpresaCreate, EmpresaResponse, EmpresaUpdate, CargoUpdate
from schemas.usuario_schema import UsuarioResponse, FuncionarioFiltro
from schemas.convite_schema import ConviteResponse
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
from utils.paginacao import Paginacao, get_paginacao
import services.empresa_service as service

# "/empresa" no singular: cada usuário pertence a no máximo uma empresa,
# então o recurso é sempre "a empresa do usuário logado".
empresa_router = APIRouter(prefix='/empresa', tags=['empresa'])

@empresa_router.post('', response_model=EmpresaResponse, status_code=201)
def criar_empresa(
    dados: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_empresa(dados, db, usuario)

@empresa_router.get('', response_model=EmpresaResponse)
def obter_empresa(db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.obter_empresa(db, usuario)

@empresa_router.patch('', response_model=EmpresaResponse)
def editar_empresa(
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_empresa(dados, db, usuario)

# --- Funcionários ---

@empresa_router.get('/funcionarios', response_model=List[UsuarioResponse])
def listar_funcionarios(
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_funcionarios(None, paginacao, db, usuario)

# Busca por nome/email/CPF/telefone: filtros no corpo para não expor dado pessoal na URL (LGPD).
@empresa_router.post('/funcionarios/busca', response_model=List[UsuarioResponse])
def buscar_funcionarios(
    filtro: FuncionarioFiltro,
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_funcionarios(filtro, paginacao, db, usuario)

@empresa_router.patch('/funcionarios/{id}', response_model=UsuarioResponse)
def editar_cargo(
    id: int,
    dados: CargoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_cargo(id, dados, db, usuario)

# Remove o vínculo com a empresa (a conta do usuário continua existindo).
@empresa_router.delete('/funcionarios/{id}', response_model=UsuarioResponse)
def remover_funcionario(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.remover_funcionario(id, db, usuario)

# --- Convites ---

@empresa_router.post('/convites', response_model=ConviteResponse, status_code=201)
def criar_convite(db: Session = Depends(get_db), usuario: Usuarios = Depends(get_current_user)):
    return service.criar_convite(db, usuario)
