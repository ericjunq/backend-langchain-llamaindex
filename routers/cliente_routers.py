from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.cliente_schema import FiltrarCliente, ClienteCreate, ClienteResponse, ClienteUpdate
from security.dependencies import get_db
from models.cliente_model import Clientes
from models.usuario_model import Usuarios
from security.security import get_current_user
from utils.enums import CargosEnum
from typing import List, Optional
from datetime import datetime
from schemas.filtrodata_schema import DataFilter, Periodo

cliente_router = APIRouter(prefix='/cliente', tags=['clientes'])

@cliente_router.post('/adicionar_cliente', response_model=ClienteResponse)
async def adicionar_cliente(
    clienteschema: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
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

@cliente_router.patch('/editar_cliente/{id}', response_model=ClienteResponse)
async def editar_cliente(
    id: int,
    dados: ClienteUpdate,
    db: Session=Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')

    cliente = db.query(Clientes).filter(
        Clientes.id == id,
        Clientes.empresa_id == usuario.empresa_id
    ).first()

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

@cliente_router.delete('/deletar_cliente/{id}')
async def deletar_cliente(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
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

    return "Cliente deletado com sucesso"

@cliente_router.get('/listar_clientes', response_model=List[ClienteResponse])
async def listar_clientes(
    periodo: Optional[Periodo] = None,
    datafilter: Optional[DataFilter]=None,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail="Use apenas um filtro por vez")
    
    query = db.query(Clientes).filter(
        Clientes.empresa_id==usuario.empresa_id
    )

    if periodo:
        inicio = datetime.now()
        if periodo.periodo == 'mes':
            inicio = inicio.replace(day=1, hour=0,minute=0,second=0,microsecond=0)
            query = query.filter(
                Clientes.created_at>=inicio
            )
        
        elif periodo.periodo == 'semestre':
            inicio = inicio.replace(day=1, hour=0,minute=0,second=0,microsecond=0)
            if inicio.month <= 6:
                inicio = inicio.replace(month=1)
                query = query.filter(
                    Clientes.created_at >= inicio
                )
            
            else:
                inicio = inicio.replace(month=7)
                query = query.filter(
                    Clientes.created_at>=inicio
                )
        
        elif periodo.periodo == 'ano':
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Clientes.created_at >= inicio
            )

    if datafilter:
        if datafilter.data_final is None:
            query = query.filter(
                Clientes.created_at>=datafilter.data_inicial
            )

        else:
            if datafilter.data_final <= datafilter.data_inicial:
                raise HTTPException(status_code=400, detail="Data final menor que inicial")
            query = query.filter(
                Clientes.created_at >= datafilter.data_inicial,
                Clientes.created_at <= datafilter.data_final
            )
        
    return query.all()

@cliente_router.get('/buscar_cliente_id/{id}', response_model=ClienteResponse)
async def buscar_cliente_id(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
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

@cliente_router.get('/buscar_cliente', response_model=List[ClienteResponse])
async def buscar_cliente(
    filtro: FiltrarCliente = Depends(),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
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

@cliente_router.get('/buscar_clientes_por_funcionario/{usuario_id}', response_model=List[ClienteResponse])
async def buscar_clientes_por_funcionario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence à nenhuma empresa')
    
    funcionario = db.query(Usuarios).filter(
        Usuarios.empresa_id == usuario.empresa_id,
        Usuarios.id == usuario_id
    ).first()
    if funcionario is None:
        raise HTTPException(status_code=404, detail='Funcionario não encontrado')
    
    clientes = db.query(Clientes).filter(
        Clientes.empresa_id==usuario.empresa_id,
        Clientes.usuario_id == usuario_id
    ).all()

    return clientes