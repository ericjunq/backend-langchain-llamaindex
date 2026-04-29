from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from security.dependencies import get_db
from schemas.usuario_schema import UsuarioResponse, UsuarioSchema, UsuarioUpdate
from security.security import verificar_senha, criptografar_senha, criar_access_token, criar_refresh_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm

usuario_router = APIRouter(prefix="/usuario", tags=["usuario"])

@usuario_router.post('/cadastro', response_model=UsuarioResponse)
async def cadastrar_usuario(
    usuarioschema: UsuarioSchema,
    db: Session=Depends(get_db)
):
    email_existente = db.query(Usuarios).filter(
        Usuarios.email == usuarioschema.email
    ).first()
    if email_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    cpf_existente = db.query(Usuarios).filter(
        Usuarios.cpf == usuarioschema.cpf
    ).first()
    if cpf_existente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    telefone_existente = db.query(Usuarios).filter(
        Usuarios.telefone == usuarioschema.telefone
    ).first()
    if telefone_existente:
        raise HTTPException(status_code=400, detail="Telefone já cadastrado")
    
    senha_criptografada = criptografar_senha(usuarioschema.senha)

    usuario = Usuarios(
        nome=usuarioschema.nome,
        sobrenome=usuarioschema.sobrenome,
        email=usuarioschema.email,
        senha_hash=senha_criptografada,
        cpf=usuarioschema.cpf,
        telefone=usuarioschema.telefone
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario

@usuario_router.post("/login")
async def login(
    dados: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuarios).filter(
        Usuarios.email == dados.username
    ).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Email incorreto")
    
    if not verificar_senha(dados.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    access_token = criar_access_token(
        data = {'sub': dados.username, 'type': 'access'}
    )

    refresh_token = criar_refresh_token(
        data = {'sub': dados.username, 'type': 'refresh'}
    )

    return {
        "access_token": access_token,
        "refresh_token":refresh_token,
        "token_type":"bearer"
    }

@usuario_router.patch('/editar_usuario', response_model=UsuarioResponse)
async def editar_usuario(
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    dados_update = dados.model_dump(exclude_unset=True)

    if 'email' in dados_update and dados_update['email']:
        email_existente = db.query(Usuarios).filter(
            Usuarios.email == dados_update['email']
        ).first()
        if email_existente and email_existente.id != usuario.id:
            raise HTTPException(status_code=400, detail='Email já cadastrado')
    
    if 'telefone' in dados_update and dados_update['telefone']:
        telefone_existente = db.query(Usuarios).filter(
            Usuarios.telefone == dados_update['telefone']
        ).first()
        if telefone_existente and telefone_existente.id != usuario.id:
            raise HTTPException(status_code=400, detail='Telefone já cadastrado')
    
    if 'senha' in dados_update:
        dados_update['senha_hash'] = criptografar_senha(dados_update.pop('senha'))
    
    for campo, valor in dados_update.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)

    return usuario