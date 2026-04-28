from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.produto_schema import ProdutoReponse, ProdutoReposicaoEstoque, ProdutoSchema, ProdutoUpdate
from security.dependencies import get_db
from models.empresa_model import Empresa
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from security.security import get_current_user
from utils.enums import CargosEnum

produto_router = APIRouter(prefix='/produtos', tags=['produtos'])

@produto_router.post('/cadastrar_produto', response_model=ProdutoReponse)
async def cadastrar_produto(
    produtoschema: ProdutoSchema,
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user)
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=404, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para cadastrar produtos')
    
    produto = Produtos(
        nome=produtoschema.nome,
        descricao=produtoschema.descricao,
        quantidade=produtoschema.quantidade,
        preco_compra=produtoschema.preco_compra,
        preco_venda=produtoschema.preco_venda,
        estoque_min=produtoschema.estoque_min
    )

    db.add(produto)
    db.commit()
    db.refresh(produto)

    return produto

