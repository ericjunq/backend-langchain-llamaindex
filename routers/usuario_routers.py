from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from models.usuario_model import Usuarios
from security.dependencies import get_db
from schemas.usuario_schema import UsuarioResponse, UsuarioSchema, UsuarioUpdate
from security.security import verificar_senha, criptografar_senha

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
        Usuarios.cpf == usuarioschema
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