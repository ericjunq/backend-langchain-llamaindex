from fastapi import HTTPException
from sqlalchemy.orm import Session
from schemas.empresa_schema import EmpresaCreate, EmpresaUpdate, CargosFuncionarios
from models.empresa_model import Empresa
from models.usuario_model import Usuarios
from utils.enums import CargosEnum
from schemas.usuario_schema import FuncionarioFiltro
from models.convite_funcionario import Convite
from utils.convidar_funcionario import gerar_convite

# Função de criar Empresa
def criar_empresa(
    empresaschema: EmpresaCreate,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is not None:
        raise HTTPException(status_code=400, detail="Usuário já pertence a uma empresa")

    email_existente = db.query(Empresa).filter(
        Empresa.email == empresaschema.email
    ).first()
    if email_existente:
        raise HTTPException(status_code=409, detail='Email já cadastrado')

    cnpj_existente = db.query(Empresa).filter(
        Empresa.cnpj == empresaschema.cnpj
    ).first()
    if cnpj_existente:
        raise HTTPException(status_code=409, detail='CNPJ já cadastrado')
    
    telefone_existente = db.query(Empresa).filter(
        Empresa.telefone == empresaschema.telefone
    ).first()
    if telefone_existente:
        raise HTTPException(status_code=409, detail='Telefone já cadastrado')
    
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

# Função de editar dados da empresa
def editar_empresa(
    dados: EmpresaUpdate,
    db: Session,
    usuario: Usuarios 
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')
    
    empresa = db.query(Empresa).filter(
        Empresa.id == usuario.empresa_id
    ).first()
    if empresa is None:
        raise HTTPException(status_code=404, detail='Empresa inexistente')
    
    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Você não tem permissão para editar a empresa')
    
    
    dados_update = dados.model_dump(exclude_unset=True)

    if 'email' in dados_update and dados_update['email']:
        email_existente = db.query(Empresa).filter(
            Empresa.email == dados_update['email']
        ).first()
        if email_existente and email_existente.id != empresa.id:
            raise HTTPException(status_code=409, detail='Email já cadastrado')
    
    if 'telefone' in dados_update and dados_update['telefone']:
        telefone_existente = db.query(Empresa).filter(
            Empresa.telefone == dados_update['telefone']
        ).first()
        if telefone_existente and telefone_existente.id != empresa.id:
            raise HTTPException(status_code=409, detail='Telefone já cadastrado')
    
    for campo, valor in dados_update.items():
        setattr(empresa, campo, valor)

    db.commit()
    db.refresh(empresa)

    return empresa

# Função pra editar cargo de um funcionário
def editar_cargo(
    id: int,
    cargo: CargosFuncionarios,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')

    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Sem permissão para editar cargos')
    
    funcionario = db.query(Usuarios).filter(
        Usuarios.id == id,
        Usuarios.empresa_id == usuario.empresa_id
    ).first()

    if funcionario is None:
        raise HTTPException(status_code=404, detail='Funcionário não encontrado ou não pertence a empresa')

    if funcionario.id == usuario.id:
        raise HTTPException(status_code=403, detail='Você não pode alterar seu próprio cargo')

    if funcionario.cargo == CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Não é possível alterar o cargo do dono')
    funcionario.cargo = cargo.cargo

    db.commit()
    db.refresh(funcionario)

    return funcionario

# Função pra remover funcionário da empresa
def remover_funcionario(
    id:int,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')
    
    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Você não tem permissão para remover um funcionário')
    
    funcionario = db.query(Usuarios).filter(
        Usuarios.id == id,
        Usuarios.empresa_id == usuario.empresa_id
    ).first()

    if funcionario is None:
        raise HTTPException(status_code=404, detail='Funcionário não encontrado')

    if funcionario.id == usuario.id:
        raise HTTPException(status_code=403, detail='Você não pode remover a si mesmo da empresa')
    
    funcionario.empresa_id = None
    funcionario.cargo = None
    db.commit()
    db.refresh(funcionario)

    return funcionario

# Função pra listar funcionários
def listar_funcionarios(
    filtro: FuncionarioFiltro,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')
    
    query = db.query(Usuarios).filter(
        Usuarios.empresa_id == usuario.empresa_id
    )
    
    if filtro.nome and filtro.nome.strip():
            query = query.filter(Usuarios.nome.ilike(f"%{filtro.nome}%"))

    if filtro.sobrenome and filtro.sobrenome.strip():
            query = query.filter(Usuarios.sobrenome.ilike(f"%{filtro.sobrenome}%"))

    if filtro.email and filtro.email.strip():
            query = query.filter(Usuarios.email.ilike(f"%{filtro.email}%"))
                
    if filtro.cpf and filtro.cpf.strip():
            query = query.filter(
                Usuarios.cpf == filtro.cpf
            )

    if filtro.telefone and filtro.telefone.strip():
            query = query.filter(
                Usuarios.telefone == filtro.telefone
            )

    return query.all()

def criar_convite(
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo != CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Você não tem permissão para criar convites')
    
    token = gerar_convite()

    convite = Convite(
        token = token,
        empresa_id=usuario.empresa_id
    )

    db.add(convite)
    db.commit()
    db.refresh(convite)

    return convite