from fastapi import HTTPException
from sqlalchemy.orm import Session
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

def exigir_proprio_se_funcionario(usuario: Usuarios, membro_id: int, detail: str) -> None:
    """Funcionário só pode consultar dados vinculados a ele mesmo."""
    if usuario.cargo == CargosEnum.funcionario and membro_id != usuario.id:
        raise HTTPException(status_code=403, detail=detail)

def exigir_membro(db: Session, usuario: Usuarios, membro_id: int) -> None:
    """404 se o usuário informado não for da mesma empresa (não revela que ele existe)."""
    existe = db.query(Usuarios.id).filter(
        Usuarios.id == membro_id,
        Usuarios.empresa_id == usuario.empresa_id
    ).first()
    if existe is None:
        raise HTTPException(status_code=404, detail='Funcionário não encontrado')
