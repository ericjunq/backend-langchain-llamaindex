from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, Query
from utils.enums import PeriodoEnum

@dataclass
class IntervaloData:
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None

def _com_fuso(data: Optional[datetime]) -> Optional[datetime]:
    # Datas sem fuso são tratadas como UTC, para não misturar datas com e sem fuso.
    if data is not None and data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)
    return data

def inicio_do_periodo(periodo: PeriodoEnum, agora: datetime) -> datetime:
    base = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if periodo == PeriodoEnum.mes:
        return base
    if periodo == PeriodoEnum.semestre:
        return base.replace(month=1 if agora.month <= 6 else 7)
    return base.replace(month=1)

def get_intervalo_data(
    periodo: Optional[PeriodoEnum] = Query(None, description='Período corrente: mes, semestre ou ano'),
    data_inicial: Optional[datetime] = Query(None, description='Início do intervalo (ISO 8601)'),
    data_final: Optional[datetime] = Query(None, description='Fim do intervalo (ISO 8601); padrão: agora'),
) -> Optional[IntervaloData]:
    """Dependência única de filtro de data (query params). Use `periodo` OU `data_inicial`/`data_final`."""
    data_inicial, data_final = _com_fuso(data_inicial), _com_fuso(data_final)

    if periodo and (data_inicial or data_final):
        raise HTTPException(status_code=400, detail='Use apenas um filtro de data por vez: período ou intervalo')

    if periodo:
        return IntervaloData(inicio=inicio_do_periodo(periodo, datetime.now(timezone.utc)))

    if data_inicial is None and data_final is None:
        return None

    if data_inicial and data_final and data_final < data_inicial:
        raise HTTPException(status_code=400, detail='Data final menor que data inicial')

    return IntervaloData(inicio=data_inicial, fim=data_final)

def filtros_intervalo(coluna, intervalo: Optional[IntervaloData]) -> list:
    """Condições SQL do intervalo para uma coluna de data (lista vazia se não houver filtro)."""
    if intervalo is None:
        return []
    condicoes = []
    if intervalo.inicio is not None:
        condicoes.append(coluna >= intervalo.inicio)
    if intervalo.fim is not None:
        condicoes.append(coluna <= intervalo.fim)
    return condicoes
