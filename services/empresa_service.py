import secrets
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from schemas.empresa_schema import EmpresaCreate, EmpresaUpdate, CargoUpdate
from schemas.usuario_schema import FuncionarioFiltro
from models.empresa_model import Empresa
from models.usuario_model import Usuarios
from models.convite_funcionario import Convite
from security.permissoes import exigir_empresa, exigir_cargo
from utils.enums import CargosEnum
from utils.paginacao import Paginacao
import services.auditoria_service as auditoria

DADOS_EM_USO = 'Email, CNPJ ou telefone já cadastrado'

def criar_empresa(empresaschema: EmpresaCreate, db: Session, usuario: Usuarios):
    if usuario.empresa_id is not None:
        raise HTTPException(status_code=400, detail="Usuário já pertence a uma empresa")

    conflito = db.query(Empresa.id).filter(or_(
        Empresa.email == empresaschema.email,
        Empresa.cnpj == empresaschema.cnpj,
        Empresa.telefone == empresaschema.telefone,
    )).first()
    if conflito:
        raise HTTPException(status_code=409, detail=DADOS_EM_USO)

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
    auditoria.registrar(db, 'empresa.criada', usuario=usuario, empresa_id=empresa.id,
                        entidade='empresa', entidade_id=empresa.id, detalhes={'nome': empresa.nome})

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=DADOS_EM_USO)
    db.refresh(empresa)

    return empresa

def editar_empresa(dados: EmpresaUpdate, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, CargosEnum.dono, detail='Você não tem permissão para editar a empresa')

    empresa = db.get(Empresa, usuario.empresa_id)
    if empresa is None:
        raise HTTPException(status_code=404, detail='Empresa inexistente')

    dados_update = {k: v for k, v in dados.model_dump(exclude_unset=True).items() if v is not None}

    condicoes = []
    if 'email' in dados_update:
        condicoes.append(Empresa.email == dados_update['email'])
    if 'telefone' in dados_update:
        condicoes.append(Empresa.telefone == dados_update['telefone'])
    if condicoes:
        conflito = db.query(Empresa.id).filter(or_(*condicoes), Empresa.id != empresa.id).first()
        if conflito:
            raise HTTPException(status_code=409, detail='Email ou telefone já cadastrado')

    for campo, valor in dados_update.items():
        setattr(empresa, campo, valor)

    if dados_update:
        auditoria.registrar(db, 'empresa.editada', usuario=usuario, entidade='empresa', entidade_id=empresa.id,
                            detalhes={'campos': auditoria.campos_alterados(dados_update)})
    db.commit()
    db.refresh(empresa)

    return empresa

def _buscar_membro(id: int, db: Session, usuario: Usuarios) -> Usuarios:
    funcionario = db.query(Usuarios).filter(
        Usuarios.id == id,
        Usuarios.empresa_id == usuario.empresa_id
    ).first()
    if funcionario is None:
        raise HTTPException(status_code=404, detail='Funcionário não encontrado')
    return funcionario

def editar_cargo(id: int, cargo: CargoUpdate, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, CargosEnum.dono, detail='Sem permissão para editar cargos')

    funcionario = _buscar_membro(id, db, usuario)

    if funcionario.id == usuario.id:
        raise HTTPException(status_code=403, detail='Você não pode alterar seu próprio cargo')

    if funcionario.cargo == CargosEnum.dono:
        raise HTTPException(status_code=403, detail='Não é possível alterar o cargo do dono')

    auditoria.registrar(db, 'funcionario.cargo_alterado', usuario=usuario, entidade='usuario',
                        entidade_id=funcionario.id,
                        detalhes={'de': funcionario.cargo.value if funcionario.cargo else None, 'para': cargo.cargo.value})
    funcionario.cargo = cargo.cargo
    db.commit()
    db.refresh(funcionario)

    return funcionario

def remover_funcionario(id: int, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, CargosEnum.dono, detail='Você não tem permissão para remover um funcionário')

    funcionario = _buscar_membro(id, db, usuario)

    if funcionario.id == usuario.id:
        raise HTTPException(status_code=403, detail='Você não pode remover a si mesmo da empresa')

    # O acesso à empresa cai na hora: get_current_user relê empresa_id do banco a cada requisição.
    auditoria.registrar(db, 'funcionario.removido', usuario=usuario, entidade='usuario', entidade_id=funcionario.id)
    funcionario.empresa_id = None
    funcionario.cargo = None
    db.commit()
    db.refresh(funcionario)

    return funcionario

def obter_empresa(db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    return db.get(Empresa, usuario.empresa_id)

def listar_funcionarios(filtro: Optional[FuncionarioFiltro], paginacao: Paginacao, db: Session, usuario: Usuarios):
    """GET /empresa/funcionarios (sem filtro) e POST /empresa/funcionarios/busca (filtros no corpo)."""
    exigir_empresa(usuario)

    query = db.query(Usuarios).filter(Usuarios.empresa_id == usuario.empresa_id)
    filtro = filtro or FuncionarioFiltro()

    if filtro.nome and filtro.nome.strip():
        query = query.filter(Usuarios.nome.ilike(f"%{filtro.nome.strip()}%"))
    if filtro.sobrenome and filtro.sobrenome.strip():
        query = query.filter(Usuarios.sobrenome.ilike(f"%{filtro.sobrenome.strip()}%"))
    if filtro.email and filtro.email.strip():
        query = query.filter(Usuarios.email.ilike(f"%{filtro.email.strip()}%"))
    if filtro.cpf:
        query = query.filter(Usuarios.cpf == filtro.cpf)
    if filtro.telefone:
        query = query.filter(Usuarios.telefone == filtro.telefone)

    return paginacao.aplicar(query.order_by(Usuarios.nome, Usuarios.id)).all()

def criar_convite(db: Session, usuario: Usuarios):
    exigir_cargo(usuario, CargosEnum.dono, detail='Você não tem permissão para criar convites')

    # 32 bytes aleatórios: colisão é impraticável e o UNIQUE do banco garante o resto.
    convite = Convite(token=secrets.token_urlsafe(32), empresa_id=usuario.empresa_id)

    db.add(convite)
    db.flush()
    auditoria.registrar(db, 'convite.criado', usuario=usuario, entidade='convite', entidade_id=convite.id)
    db.commit()
    db.refresh(convite)

    return convite
