from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.empresa_schema import EmpresaCreate, EmpresaResponse, EmpresaUpdate, CargosFuncionarios
from security.dependencies import get_db
from models.empresa_model import Empresa
from models.usuario_model import Usuarios
from security.security import get_current_user
from utils.enums import CargosEnum
from schemas.usuario_schema import UsuarioResponse, FuncionarioFiltro
from typing import List
from models.convite_funcionario import Convite
from utils.convidar_funcionario import gerar_convite
from schemas.convite_schema import ConviteResponse
import services.empresa_service

empresa_router = APIRouter(prefix='/empresa', tags=['empresa'])

@empresa_router.post('/criar_empresa', response_model=EmpresaResponse   )
async def criar_empresa(
    empresaschema: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.empresa_service.criar_empresa(empresaschema, db, usuario)

@empresa_router.patch('/editar_empresa', response_model=EmpresaResponse)
async def editar_empresa(
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.empresa_service.editar_empresa(dados, db, usuario)

@empresa_router.patch('/editar_cargo_funcionario/{id}', response_model=UsuarioResponse)
async def editar_cargo(
    id: int,
    cargo: CargosFuncionarios,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.empresa_service.editar_cargo(id, cargo, db, usuario)

@empresa_router.patch('/remover_funcionario/{id}', response_model=UsuarioResponse)
async def remover_funcionario(
    id:int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.empresa_service.remover_funcionario(id, db, usuario)

@empresa_router.get('/listar_funcionarios', response_model=List[UsuarioResponse])
async def listar_funcionarios(
    filtro: FuncionarioFiltro = Depends(),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.empresa_service.listar_funcionarios(filtro, db, usuario)

@empresa_router.post('/gerar_convite', response_model=ConviteResponse)
async def criar_convite(
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    return services.empresa_service.criar_convite(db, usuario)