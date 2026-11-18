from fastapi import HTTPException
from models.usuario_model import Usuarios
from utils.enums import CargosEnum

GESTORES = (CargosEnum.dono, CargosEnum.admin)

def exigir_empresa(usuario: Usuarios) -> None:
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')

def exigir_cargo(usuario: Usuarios, *cargos: CargosEnum, detail: str = 'Você não tem permissão para isso') -> None:
    exigir_empresa(usuario)
    if usuario.cargo not in cargos:
        raise HTTPException(status_code=403, detail=detail)
