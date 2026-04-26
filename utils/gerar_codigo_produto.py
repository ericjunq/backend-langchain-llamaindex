from uuid import uuid4
from sqlalchemy.orm import Session

def gerar_codigo_produto(db: Session):
    from models.produto_model import Produto  # 👈 IMPORT AQUI DENTRO

    while True:
        codigo = "PROD-" + uuid4().hex[:8].upper()
        existe = db.query(Produto).filter(Produto.codigo_produto == codigo).first()
        if not existe:
            return codigo