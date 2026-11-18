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

empresa_router = APIRouter(prefix='/empresa', tags=['empresa'])

@empresa_router.post('/criar_empresa', response_model=EmpresaResponse, status_code=201)
def criar_empresa(
    empresaschema: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_empresa(empresaschema, db, usuario)

@empresa_router.patch('/editar_empresa', response_model=EmpresaResponse)
def editar_empresa(
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_empresa(dados, db, usuario)

@empresa_router.patch('/editar_cargo_funcionario/{id}', response_model=UsuarioResponse)
def editar_cargo(
    id: int,
    cargo: CargoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.editar_cargo(id, cargo, db, usuario)

@empresa_router.patch('/remover_funcionario/{id}', response_model=UsuarioResponse)
def remover_funcionario(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.remover_funcionario(id, db, usuario)

@empresa_router.get('/listar_funcionarios', response_model=List[UsuarioResponse])
def listar_funcionarios(
    filtro: FuncionarioFiltro = Depends(),
    paginacao: Paginacao = Depends(get_paginacao),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.listar_funcionarios(filtro, paginacao, db, usuario)

@empresa_router.post('/gerar_convite', response_model=ConviteResponse, status_code=201)
def criar_convite(
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return service.criar_convite(db, usuario)
