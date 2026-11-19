from typing import Literal, Optional
from pydantic import BaseModel


class FiltroAuditoria(BaseModel):
    """Filtros de GET /auditoria (query params: só ids e códigos, nada pessoal)."""
    categoria: Optional[Literal['acesso', 'operacao', 'venda']] = None
    acao: Optional[str] = None
    entidade: Optional[str] = None
    entidade_id: Optional[str] = None
    usuario_id: Optional[int] = None
    origem: Optional[Literal['api', 'chat']] = None
