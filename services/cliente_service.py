from fastapi import HTTPException
from sqlalchemy.orm import Session
from schemas.cliente_schema import FiltrarCliente, ClienteCreate, ClienteUpdate
from models.cliente_model import Clientes
from models.usuario_model import Usuarios
from utils.enums import CargosEnum, DataFilter as DFEnum
from typing import List, Optional
from datetime import datetime, timezone
from schemas.filtrodata_schema import DataFilter, Periodo
from datetime import datetime

# Função de adicionar cliente
def adicionar_cliente(
    clienteschema: ClienteCreate,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')

    email_existente = db.query(Clientes).filter(
        Clientes.email == clienteschema.email,
        Clientes.empresa_id == usuario.empresa_id
    ).first()
    if email_existente:
        raise HTTPException(status_code=400, detail='Cliente com esse email já cadastrado')
    
    cpf_existente = db.query(Clientes).filter(
        Clientes.cpf == clienteschema.cpf,
        Clientes.empresa_id == usuario.empresa_id
    ).first()
    if cpf_existente:
        raise HTTPException(status_code=400, detail='Cliente com esse CPF já cadastrado')
    
    cliente = Clientes(
        nome=clienteschema.nome,
        email=clienteschema.email,
        cpf=clienteschema.cpf,
        telefone=clienteschema.telefone,
        empresa_id= usuario.empresa_id,
        usuario_id=usuario.id
    )

    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return cliente

# Função para editar cliente
def editar_cliente(
    id: int,
    dados: ClienteUpdate,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')

    cliente = db.query(Clientes).filter(
        Clientes.id == id,
        Clientes.empresa_id == usuario.empresa_id
    ).first()

    if usuario.cargo == CargosEnum.funcionario and cliente.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail='Você só pode editar seus próprios clientes')

    if cliente is None:
        raise HTTPException(status_code=404, detail='Cliente não encontrado')
    
    dados_update = dados.model_dump(exclude_unset=True)

    if 'email' in dados_update and dados_update['email']:
        email_existente = db.query(Clientes).filter(
            Clientes.email == dados_update['email'],
            Clientes.empresa_id == usuario.empresa_id
        ).first()
        if email_existente and email_existente.id != cliente.id:
            raise HTTPException(status_code=409, detail='Esse email já está em uso')

    for campo, valor in dados_update.items():
        setattr(cliente, campo, valor)
    
    db.commit()
    db.refresh(cliente)

    return cliente

# Função para deletar cliente
def deletar_cliente(
    id: int,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para deletar clientes')
    
    cliente = db.query(Clientes).filter(
        Clientes.id==id,
        Clientes.empresa_id == usuario.empresa_id
    ).first()
    
    if cliente is None:
        raise HTTPException(status_code=404, detail='Cliente não encontrado')
    
    db.delete(cliente)
    db.commit()

    return {"message": "Cliente deletado com sucesso"}

# Função para listar clientes
def listar_clientes(
    db: Session,
    usuario: Usuarios,
    periodo: Optional[Periodo] = None,
    datafilter: Optional[DataFilter]=None
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail="Use apenas um filtro por vez")
    
    query = db.query(Clientes).filter(
        Clientes.empresa_id==usuario.empresa_id
    )

    if periodo:
        inicio = datetime.now(timezone.utc)
        if periodo.periodo == DFEnum.mes:
            inicio = inicio.replace(day=1, hour=0,minute=0,second=0,microsecond=0)
            query = query.filter(
                Clientes.created_at>=inicio
            )
        
        elif periodo.periodo == DFEnum.semestre:
            inicio = inicio.replace(day=1, hour=0,minute=0,second=0,microsecond=0)
            if inicio.month <= 6:
                inicio = inicio.replace(month=1)
            else:
                inicio = inicio.replace(month=7)
                
            query = query.filter(
                    Clientes.created_at>=inicio
                )
                
        
        elif periodo.periodo == DFEnum.ano:
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Clientes.created_at >= inicio
            )

    if datafilter:
        query = query.filter(
            Clientes.created_at >= datafilter.data_inicial,
            Clientes.created_at <= datafilter.data_final
        )
        
    return query.all()

# Buscar cliente por ID
def buscar_cliente_id(
    id: int,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    cliente = db.query(Clientes).filter(
        Clientes.id == id,
        Clientes.empresa_id == usuario.empresa_id
    ).first()

    if cliente is None:
        raise HTTPException(status_code=404, detail='Cliente não encontrado')
    
    return cliente

# Buscar cliente por nome, email, cpf, telefone
def buscar_cliente(
    filtro: FiltrarCliente,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    query = db.query(Clientes).filter(
        Clientes.empresa_id == usuario.empresa_id
    )
    if filtro.nome and filtro.nome.split():
            query = query.filter(Clientes.nome.ilike(f"%{filtro.nome}%"))

    if filtro.email and filtro.email.strip():
            query = query.filter(Clientes.email.ilike(f"%{filtro.email}%"))
    
    if filtro.cpf and filtro.cpf.strip():
        query = query.filter(
            Clientes.cpf == filtro.cpf
        )
    
    if filtro.telefone and filtro.telefone.strip():
        query = query.filter(
            Clientes.telefone == filtro.telefone
        )
    
    return query.all()

# Buscar clientes de um funcionário
# Dono e Admin podem listar todos os clientes de qualquer funcionário
# Funcionário só pode listar os próprios clientes
def buscar_clientes_por_funcionario(
    usuario_id: int,
    db: Session,
    usuario: Usuarios,
    periodo: Optional[Periodo]=None,
    datafilter: Optional[DataFilter]=None
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')
    
    funcionario = db.query(Usuarios).filter(
        Usuarios.empresa_id == usuario.empresa_id,
        Usuarios.id == usuario_id
    ).first()
    if funcionario is None:
        raise HTTPException(status_code=404, detail='Funcionario não encontrado')
    
    if usuario.cargo == CargosEnum.funcionario and usuario.id != funcionario.id:
        raise HTTPException(status_code=403, detail="Você só pode listar seus próprios funcionários")

    query = db.query(Clientes).filter(
        Clientes.empresa_id==usuario.empresa_id,
        Clientes.usuario_id == funcionario.id
    )

    if periodo:
        inicio = datetime.now(timezone.utc)
        if periodo.periodo == DFEnum.mes:
            inicio = inicio.replace(day=1, hour=0,minute=0,second=0,microsecond=0)
            query = query.filter(
                Clientes.created_at>=inicio
            )
        
        elif periodo.periodo == DFEnum.semestre:
            inicio = inicio.replace(day=1, hour=0,minute=0,second=0,microsecond=0)
            if inicio.month <= 6:
                inicio = inicio.replace(month=1)
            else:
                inicio = inicio.replace(month=7)
                
            query = query.filter(
                    Clientes.created_at>=inicio
                )
                
        
        elif periodo.periodo == DFEnum.ano:
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Clientes.created_at >= inicio
            )

    if datafilter:
        query = query.filter(
            Clientes.created_at >= datafilter.data_inicial,
            Clientes.created_at <= datafilter.data_final
        )
        
    return query.all()