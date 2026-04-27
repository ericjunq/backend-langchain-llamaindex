from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.cliente_schema import ClienteCreate, ClienteResponse, ClienteUpdate
from security.dependencies import get_db
from models.cliente_model import Clientes
from models.usuario_model import Usuarios
from security.security import get_current_user

cliente_router = APIRouter(prefix='/cliente', tags=['clientes'])

@cliente_router.post('/adicionar_cliente', response_model=ClienteResponse)
async def adicionar_cliente(
    clienteschema: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=404, detail='Você não pertence à nenhuma empresa')

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
        empresa_id= usuario.empresa_id
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
    cliente = db.query(Clientes).filter(
        Clientes.id == id,
        Clientes.empresa_id == usuario.empresa_id
    ).first()

    if cliente is None:
        raise HTTPException(status_code=404, detail='Cliente não encontrado')
    
    dados_update = dados.dict(exclude_unset=True)

    if 'email' in dados_update and dados_update['email']:
        email_existente = db.query(Clientes).filter(
            Clientes.email == dados_update['email']
        ).first()
        if email_existente and email_existente.id != cliente.id:
            raise HTTPException(status_code=400, detail='Esse email já está em uso')

    for campo, valor in dados_update.items():
        setattr(cliente, campo, valor)
    
    db.commit()
    db.refresh(cliente)

    return cliente