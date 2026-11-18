from dataclasses import dataclass
from fastapi import Query

@dataclass
class Paginacao:
    limite: int
    offset: int

    def aplicar(self, query):
        return query.limit(self.limite).offset(self.offset)

def get_paginacao(
    limite: int = Query(50, ge=1, le=200, description='Itens por página (máx. 200)'),
    offset: int = Query(0, ge=0, description='Quantos itens pular'),
) -> Paginacao:
    return Paginacao(limite=limite, offset=offset)
