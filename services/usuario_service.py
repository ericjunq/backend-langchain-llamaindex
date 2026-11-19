from models.usuario_model import Usuarios
from models.convite_funcionario import Convite
from schemas.usuario_schema import UsuarioSchema, UsuarioUpdate
from schemas.convite_schema import UsarConvite
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException
from security.security import verificar_senha, criptografar_senha, HASH_FALSO
from services.refresh_token_service import emitir_tokens, revogar_todos
import services.email_service as email_service
from security.limite_tentativas import limite_login
from utils.enums import CargosEnum
from datetime import datetime, timezone

DADOS_EM_USO = 'Email, CPF ou telefone já cadastrado'

def cadastrar_usuario(usuarioschema: UsuarioSchema, db: Session):
    # Uma consulta só para os três campos únicos.
    conflito = db.query(Usuarios.id).filter(or_(
        Usuarios.email == usuarioschema.email,
        Usuarios.cpf == usuarioschema.cpf,
        Usuarios.telefone == usuarioschema.telefone,
    )).first()
    if conflito:
        raise HTTPException(status_code=409, detail=DADOS_EM_USO)

    usuario = Usuarios(
        nome=usuarioschema.nome,
        sobrenome=usuarioschema.sobrenome,
        email=usuarioschema.email,
        senha_hash=criptografar_senha(usuarioschema.senha),
        cpf=usuarioschema.cpf,
        telefone=usuarioschema.telefone
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:  # cadastro simultâneo com os mesmos dados
        db.rollback()
        raise HTTPException(status_code=409, detail=DADOS_EM_USO)
    db.refresh(usuario)

    return usuario

def login(email: str, senha: str, db: Session, ip: str = 'desconhecido') -> dict:
    email = email.strip().lower()
    chave = f'{ip}|{email}'
    limite_login.verificar(chave)  # antes de qualquer consulta: barra força bruta sem custo de banco/hash

    usuario = db.query(Usuarios).filter(Usuarios.email == email).first()

    # Sempre verifica um hash (mesmo sem usuário) e sempre responde 401:
    # não revela se o email existe (LGPD / enumeração de contas).
    senha_ok = verificar_senha(senha, usuario.senha_hash if usuario else HASH_FALSO)
    if usuario is None or not senha_ok or not usuario.status:
        limite_login.registrar_falha(chave)
        raise HTTPException(status_code=401, detail='Credenciais inválidas')

    limite_login.limpar(chave)
    return emitir_tokens(usuario.id, db)

def editar_usuario(db: Session, dados: UsuarioUpdate, usuario: Usuarios):
    dados_update = {
        campo: valor
        for campo, valor in dados.model_dump(exclude_unset=True, exclude={'senha_atual'}).items()
        if valor is not None
    }
    if not dados_update:
        return usuario

    if 'email' in dados_update or 'senha' in dados_update:
        if not dados.senha_atual or not verificar_senha(dados.senha_atual, usuario.senha_hash):
            raise HTTPException(status_code=401, detail='Senha atual incorreta')

    condicoes = []
    if 'email' in dados_update:
        condicoes.append(Usuarios.email == dados_update['email'])
    if 'telefone' in dados_update:
        condicoes.append(Usuarios.telefone == dados_update['telefone'])
    if condicoes:
        conflito = db.query(Usuarios.id).filter(or_(*condicoes), Usuarios.id != usuario.id).first()
        if conflito:
            raise HTTPException(status_code=409, detail='Email ou telefone já cadastrado')

    trocou_senha = 'senha' in dados_update
    email_antigo = usuario.email
    trocou_email = 'email' in dados_update and dados_update['email'] != email_antigo

    if trocou_senha:
        dados_update['senha_hash'] = criptografar_senha(dados_update.pop('senha'))
        # Troca de senha encerra as outras sessões.
        revogar_todos(usuario.id, db)

    for campo, valor in dados_update.items():
        setattr(usuario, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Email ou telefone já cadastrado')
    db.refresh(usuario)

    # Transparência (LGPD): avisos só depois do commit (não avisa o que não aconteceu).
    if trocou_senha:
        email_service.avisar_senha_alterada(usuario.nome, usuario.email)
    if trocou_email:
        email_service.avisar_email_alterado(usuario.nome, email_antigo, usuario.email)
    return usuario

def exportar_meus_dados(db: Session, usuario: Usuarios) -> dict:
    """Direito de acesso (LGPD art. 18): tudo o que o sistema guarda sobre o titular.
    4 consultas, todas por índice (usuario_id). Dados de clientes cadastrados por ele não entram:
    pertencem aos clientes e à empresa, não ao titular."""
    from models.empresa_model import Empresa
    from models.cliente_model import Clientes
    from models.refresh_token import RefreshToken
    from models.vendas_model import Vendas
    from sqlalchemy import func

    empresa = db.get(Empresa, usuario.empresa_id) if usuario.empresa_id else None
    agora = datetime.now(timezone.utc)
    sessoes = (
        db.query(RefreshToken.created_at, RefreshToken.expires_at)
        .filter(RefreshToken.usuario_id == usuario.id, RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > agora)
        .order_by(RefreshToken.created_at.desc())
        .all()
    )

    return {
        'gerado_em': agora,
        'perfil': {
            'id': usuario.id, 'nome': usuario.nome, 'sobrenome': usuario.sobrenome, 'email': usuario.email,
            'cpf': usuario.cpf, 'telefone': usuario.telefone,
            'cargo': usuario.cargo.value if usuario.cargo else None,
            'conta_ativa': usuario.status, 'criado_em': usuario.created_at, 'atualizado_em': usuario.updated_at,
        },
        'empresa': {'id': empresa.id, 'nome': empresa.nome, 'cnpj': empresa.cnpj} if empresa else None,
        'sessoes_ativas': [{'iniciada_em': s.created_at, 'expira_em': s.expires_at} for s in sessoes],
        'atividade': {
            'vendas_registradas': db.query(func.count(Vendas.id)).filter(Vendas.usuario_id == usuario.id).scalar(),
            'clientes_cadastrados': db.query(func.count(Clientes.id)).filter(Clientes.usuario_id == usuario.id).scalar(),
        },
        'observacoes': [
            'Senhas e tokens são guardados apenas como hash e não podem ser exportados.',
            'Dados dos clientes que você cadastrou pertencem a eles e à empresa, por isso não estão aqui.',
        ],
    }

def vincular_empresa(token: UsarConvite, db: Session, usuario: Usuarios):
    if usuario.empresa_id:
        raise HTTPException(status_code=403, detail='Você já está vinculado a uma empresa')

    # FOR UPDATE: impede que o mesmo convite seja usado duas vezes ao mesmo tempo.
    convite = db.query(Convite).filter(Convite.token == token.token).with_for_update().first()
    if convite is None:
        raise HTTPException(status_code=404, detail='Convite inválido ou não encontrado')

    if convite.usado:
        raise HTTPException(status_code=409, detail='Convite já utilizado')

    expira = convite.expires_at
    if expira.tzinfo is None:  # alguns bancos (ex.: SQLite) devolvem sem fuso
        expira = expira.replace(tzinfo=timezone.utc)
    if expira <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail='Convite expirado')

    usuario.empresa_id = convite.empresa_id
    usuario.cargo = CargosEnum.funcionario
    convite.usuario_id = usuario.id
    convite.usado = True

    db.commit()
    db.refresh(usuario)

    return usuario
