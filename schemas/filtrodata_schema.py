from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from utils.enums import DataFilter

class Periodo(BaseModel):
    periodo: DataFilter

class DataFilter(BaseModel):
    data_inicial: Optional[datetime] = None
    data_final: Optional[datetime] = None