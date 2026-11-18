from typing import Optional
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from schemas.cliente_schema import FiltrarCliente, ClienteCreate, ClienteUpdate
from models.cliente_model import Clientes
from models.usuario_model import Usuarios
from models.vendas_model import Vendas
from security.permissoes import exigir_empresa, exigir_cargo, GESTORES
from utils.enums import CargosEnum
from utils.data_filter import IntervaloData, filtros_intervalo
from utils.paginacao import Paginacao

def _query_ativos(db: Session, usuario: Usuarios):
    return db.query(Clientes).filter(
        Clientes.empresa_id == usuario.empresa_id,
        Clientes.status.is_(True)
    )

def _buscar_cliente(id: int, db: Session, usuario: Usuarios) -> Clientes:
    cliente = _query_ativos(db, usuario).filter(Clientes.id == id).first()
    if cliente is None:
        raise HTTPException(status_code=404, detail='Cliente não encontrado')
    return cliente

def _checar_conflito(db: Session, usuario: Usuarios, email=None, cpf=None, ignorar_id=None):
    condicoes = []
    if email:
        condicoes.append(Clientes.email == email)
    if cpf:
        condicoes.append(Clientes.cpf == cpf)
    if not condicoes:
        return
    query = db.query(Clientes.id).filter(Clientes.empresa_id == usuario.empresa_id, or_(*condicoes))
    if ignorar_id is not None:
        query = query.filter(Clientes.id != ignorar_id)
    if query.first():
        raise HTTPException(status_code=409, detail='Cliente com esse email ou CPF já cadastrado')

def adicionar_cliente(clienteschema: ClienteCreate, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    _checar_conflito(db, usuario, email=clienteschema.email, cpf=clienteschema.cpf)

    cliente = Clientes(
        nome=clienteschema.nome,
        email=clienteschema.email,
        cpf=clienteschema.cpf,
        telefone=clienteschema.telefone,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id
    )
    db.add(cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Cliente com esse email ou CPF já cadastrado')
    db.refresh(cliente)

    return cliente

def editar_cliente(id: int, dados: ClienteUpdate, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    cliente = _buscar_cliente(id, db, usuario)

    if usuario.cargo == CargosEnum.funcionario and cliente.usuario_id != usuario.id:
        raise HTTPException(status_code=403, detail='Você só pode editar seus próprios clientes')

    dados_update = {k: v for k, v in dados.model_dump(exclude_unset=True).items() if v is not None}
    _checar_conflito(db, usuario, email=dados_update.get('email'), ignorar_id=cliente.id)

    for campo, valor in dados_update.items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)

    return cliente

def deletar_cliente(id: int, db: Session, usuario: Usuarios):
    exigir_cargo(usuario, *GESTORES, detail='Você não tem permissão para deletar clientes')
    cliente = _buscar_cliente(id, db, usuario)

    tem_vendas = db.query(Vendas.id).filter(Vendas.cliente_id == cliente.id).first() is not None

    if not tem_vendas:
        db.delete(cliente)
        db.commit()
        return {"message": "Cliente deletado com sucesso"}

    # Com vendas, o registro precisa ficar (histórico financeiro), mas os dados
    # pessoais perdem a finalidade: anonimiza (LGPD).
    cliente.nome = 'Cliente anonimizado'
    cliente.email = None
    cliente.cpf = None
    cliente.telefone = None
    cliente.status = False
    db.commit()

    return {"message": "Cliente possui vendas: dados pessoais anonimizados e cadastro desativado"}

def listar_clientes(
    db: Session,
    usuario: Usuarios,
    paginacao: Paginacao,
    intervalo: Optional[IntervaloData] = None,
):
    exigir_empresa(usuario)
    query = _query_ativos(db, usuario).filter(*filtros_intervalo(Clientes.created_at, intervalo))
    return paginacao.aplicar(query.order_by(Clientes.created_at.desc(), Clientes.id.desc())).all()

def buscar_cliente_id(id: int, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    return _buscar_cliente(id, db, usuario)

def buscar_cliente(filtro: FiltrarCliente, paginacao: Paginacao, db: Session, usuario: Usuarios):
    exigir_empresa(usuario)
    query = _query_ativos(db, usuario)

    if filtro.nome and filtro.nome.strip():
        query = query.filter(Clientes.nome.ilike(f"%{filtro.nome.strip()}%"))
    if filtro.email and filtro.email.strip():
        query = query.filter(Clientes.email.ilike(f"%{filtro.email.strip()}%"))
    if filtro.cpf:
        query = query.filter(Clientes.cpf == filtro.cpf)
    if filtro.telefone:
        query = query.filter(Clientes.telefone == filtro.telefone)

    return paginacao.aplicar(query.order_by(Clientes.nome, Clientes.id)).all()

# Dono e Admin podem listar os clientes de qualquer funcionário.
# Funcionário só pode listar os próprios clientes.
def buscar_clientes_por_funcionario(
    usuario_id: int,
    db: Session,
    usuario: Usuarios,
    paginacao: Paginacao,
    intervalo: Optional[IntervaloData] = None,
):
    exigir_empresa(usuario)

    if usuario.cargo == CargosEnum.funcionario and usuario.id != usuario_id:
        raise HTTPException(status_code=403, detail="Você só pode listar seus próprios clientes")

    funcionario = db.query(Usuarios.id).filter(
        Usuarios.empresa_id == usuario.empresa_id,
        Usuarios.id == usuario_id
    ).first()
    if funcionario is None:
        raise HTTPException(status_code=404, detail='Funcionário não encontrado')

    query = _query_ativos(db, usuario).filter(
        Clientes.usuario_id == usuario_id,
        *filtros_intervalo(Clientes.created_at, intervalo)
    )
    return paginacao.aplicar(query.order_by(Clientes.created_at.desc(), Clientes.id.desc())).all()
