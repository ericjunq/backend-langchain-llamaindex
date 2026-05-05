from fastapi import HTTPException
from sqlalchemy.orm import Session
from schemas.produto_schema import FiltrarProdutos, ProdutoReposicaoEstoque, ProdutoSchema, ProdutoUpdate
from models.produto_model import Produtos
from models.usuario_model import Usuarios
from utils.enums import CargosEnum
from schemas.filtrodata_schema import DataFilter, Periodo
from datetime import datetime, timezone
from utils.normalizar_nome import normalizar_nome

# Função para cadastro de produtos
def cadastrar_produto(
    produtoschema: ProdutoSchema,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=404, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para cadastrar produtos')
    
    nome_padronizado = normalizar_nome(produtoschema.nome)
    
    produto = Produtos(
        nome=produtoschema.nome,
        nome_normalizado=nome_padronizado,
        descricao=produtoschema.descricao,
        quantidade=produtoschema.quantidade,
        preco_compra=produtoschema.preco_compra,
        preco_venda=produtoschema.preco_venda,
        estoque_min=produtoschema.estoque_min
    )
    produto.empresa_id = usuario.empresa_id

    db.add(produto)
    db.commit()
    db.refresh(produto)

    return produto

# Função para editar produto
def editar_produto(
    id: int,
    dados: ProdutoUpdate,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para fazer isso')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    dados_update = dados.model_dump(exclude_unset=True)

    for campo, valor in dados_update.items():
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)

    return produto

# Função para deletar produto
def deletar_produto(
    id:int,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if usuario.cargo == CargosEnum.funcionario:
        raise HTTPException(status_code=403, detail='Você não tem permissão para fazer isso')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    db.delete(produto)
    db.commit()

    return {'message':'Produto deletado com sucesso'}

# Função para repor estoque de um produto
def repor_estoque(
    id: int,
    dados: ProdutoReposicaoEstoque,
    db: Session,
    usuario: Usuarios
): 
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    nova_quantidade = dados.quantidade
    produto.quantidade += nova_quantidade

    db.commit()
    db.refresh(produto)

    return produto

# Função para listar produtos (Baseado em período)
def listar_produtos(
    datafilter: DataFilter,
    periodo: Periodo,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    if periodo and datafilter:
        raise HTTPException(status_code=400, detail='Use apenas um filtro por vez')
    
    query = db.query(Produtos).filter(
        Produtos.empresa_id == usuario.empresa_id
    )

    if periodo:
        inicio = datetime.now(timezone.utc)
        if periodo.periodo == 'mes': 
            inicio = inicio.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
            query = query.filter(
                Produtos.created_at >= inicio
            )
        if periodo.periodo == 'semestre':
            inicio = inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if inicio.month <= 6:
                inicio = inicio.replace(month=1)
            else:
                inicio = inicio.replace(month=7)
            query = query.filter(
                Produtos.created_at >= inicio
            )
        if periodo.periodo == 'ano':
            inicio = inicio.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                Produtos.created_at >= inicio
            )

    if datafilter:
        query = query.filter(
            Produtos.created_at >= datafilter.data_inicial,
            Produtos.created_at <= datafilter.data_final
        )

    return query.all()

# Buscar um produto específico para ver as informações dele
def buscar_produto_por_id(
    id: int, 
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    produto = db.query(Produtos).filter(
        Produtos.id == id,
        Produtos.empresa_id == usuario.empresa_id
    ).first()

    if produto is None:
        raise HTTPException(status_code=404, detail='Produto não encontrado')
    
    return produto

# Buscar produtos por nomes/código do produto/preço da venda/preço de compra/quantidade mínima de estoque
def buscar_produto(
    filtros: FiltrarProdutos,
    db: Session,
    usuario: Usuarios
):
    if usuario.empresa_id is None:
        raise HTTPException(status_code=403, detail='Você não pertence a nenhuma empresa')
    
    query = db.query(Produtos).filter(
        Produtos.empresa_id == usuario.empresa_id
    )

    if filtros.nome and filtros.nome.strip():
        nome_normalizado = normalizar_nome(filtros.nome)
        query = query.filter(
            Produtos.nome_normalizado.ilike(f"%{nome_normalizado}%")
        )
    if filtros.codigo_produto and filtros.codigo_produto.strip():
        query = query.filter(
            Produtos.codigo_produto == filtros.codigo_produto
        )
    if filtros.preco_compra and filtros.preco_compra.strip():
        query = query.filter(
            Produtos.preco_compra == filtros.preco_compra
        )
    if filtros.preco_venda and filtros.preco_venda.strip():
        query = query.filter(
            Produtos.preco_venda == filtros.preco_venda
        )
    if filtros.estoque_min and filtros.estoque_min.strip():
        query = query.filter(
            Produtos.estoque_min == filtros.estoque_min
        )

    return query.all()