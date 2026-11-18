from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from security.dependencies import get_db
from security.security import get_current_user
from models.usuario_model import Usuarios
from utils.data_filter import IntervaloData, get_intervalo_data
import services.relatorio_service as service

relatorio_router = APIRouter(prefix='/relatorios', tags=['relatórios'])

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def _arquivo_xlsx(conteudo: bytes, prefixo: str) -> Response:
    nome = f'{prefixo}_{datetime.now():%Y%m%d_%H%M}.xlsx'
    return Response(
        content=conteudo,
        media_type=XLSX,
        headers={
            'Content-Disposition': f'attachment; filename="{nome}"',
            'Cache-Control': 'no-store',  # pode conter dados pessoais: não guardar em cache
        },
    )

# --- Vendas (só dono) ---

@relatorio_router.get('/vendas')
def relatorio_vendas(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.relatorio_vendas(db, usuario, intervalo)

@relatorio_router.get('/vendas/exportar')
def exportar_relatorio_vendas(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return _arquivo_xlsx(service.exportar_relatorio_vendas(db, usuario, intervalo), 'relatorio_vendas')

# --- Produtos (dono e admin) ---

@relatorio_router.get('/produtos')
def relatorio_produtos(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return service.relatorio_produtos(db, usuario, intervalo)

@relatorio_router.get('/produtos/exportar')
def exportar_relatorio_produtos(
    intervalo: Optional[IntervaloData] = Depends(get_intervalo_data),
    db: Session = Depends(get_db),
    usuario: Usuarios = Depends(get_current_user),
):
    return _arquivo_xlsx(service.exportar_relatorio_produtos(db, usuario, intervalo), 'relatorio_produtos')
