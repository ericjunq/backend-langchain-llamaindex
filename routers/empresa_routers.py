from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.empresa_schema import EmpresaCreate, EmpresaResponse, EmpresaUpdate
from security.dependencies import get_db
from models.empresa_model import Empresa
from models.usuario_model import Usuarios
from security.security import get_current_user
from utils.enums import CargosEnum

empresa_router = APIRouter(prefix='/empresa', tags=['empresa'])

@empresa_router.post('/criar_empresa', response_model=EmpresaResponse)
async def criar_empresa(
    empresaschema: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    email_existente = db.query(Empresa).filter(
        Empresa.email == empresaschema.email
    ).first()
    if email_existente:
        raise HTTPException(status_code=400, detail='Email já cadastrado')

    cnpj_existente = db.query(Empresa).filter(
        Empresa.cnpj == empresaschema.cnpj
    ).filter()
    if cnpj_existente:
        raise HTTPException(status_code=400, detail='CNPJ já cadastrado')
    
    telefone_existente = db.query(Empresa).filter(
        Empresa.telefone == empresaschema.telefone
    ).first()
    if telefone_existente:
        raise HTTPException(status_code=400, detail='Telefone já cadastrado')
    
    if usuario.empresa_id is not None:
        raise HTTPException(
        status_code=400,
        detail="Usuário já pertence a uma empresa"
    )
    
    empresa = Empresa(
        nome=empresaschema.nome,
        cnpj=empresaschema.cnpj,
        email=empresaschema.email,
        telefone=empresaschema.telefone
    )
    db.add(empresa)
    db.flush()

    usuario.cargo = CargosEnum.dono
    usuario.empresa_id = empresa.id

    db.commit()
    db.refresh(empresa)
    db.refresh(usuario)

    return empresa

@empresa_router.patch('/editar_empresa', response_model=EmpresaResponse)
async def editar_empresa(
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=404, detail='Você não pertence à nenhuma empresa')
    
    empresa = db.query(Empresa).filter(
        Empresa.id == usuario.empresa_id
    ).first()
    if empresa is None:
        raise HTTPException(status_code=404, detail='Empresa inexistente')
    
    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Você não tem permissão para editar a empresa')
    
    
    dados_update = dados.dict(exclude_unset=True)

    if 'email' in dados_update:
        email_existente = db.query(Empresa).filter(
            Empresa.email == dados_update['email']
        ).first()
        if email_existente and email_existente.id != empresa.id:
            raise HTTPException(status_code=400, detail='Email já cadastrado')
    
    if 'telefone' in dados_update:
        telefone_existente = db.query(Empresa).filter(
            Empresa.telefone == dados_update['telefone']
        ).first()
        if telefone_existente and telefone_existente.id != empresa.id:
            raise HTTPException(status_code=400, detail='Telefone já cadastrado')
    
    for campo, valor in dados_update.items():
        setattr(empresa, campo, valor)

    db.commit()
    db.refresh(empresa)

    return empresa