from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field


class MensagemHistorico(BaseModel):
    papel: Literal['usuario', 'assistente']
    conteudo: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    # O histórico fica no FRONTEND (o servidor não guarda conversas: LGPD). Só as últimas 10.
    historico: List[MensagemHistorico] = Field(default_factory=list, max_length=10)


class AcaoPendenteResponse(BaseModel):
    id: str
    tipo: str
    resumo: str
    expires_at: datetime


class ChatResponse(BaseModel):
    resposta: str
    ferramentas_usadas: List[str] = []
    acoes_pendentes: List[AcaoPendenteResponse] = []
