from uuid import uuid4
from sqlalchemy.orm import Session
from models.convite_funcionario import Convite

def gerar_convite(db: Session):
    while True:
        token = str(uuid4())
        token_existente = db.query(Convite).filter(
            Convite.token == token
        ).first()
        if not token_existente:
            break
        
    return token