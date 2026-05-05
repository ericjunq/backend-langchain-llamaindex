from pydantic import BaseModel
from datetime import datetime


class UsarConvite(BaseModel):
    token: str

class ConviteResponse(BaseModel):
    token: str
    usuario_id: int
    empresa_id: int
    created_at: datetime
    expires_at: datetime
    usado: bool
