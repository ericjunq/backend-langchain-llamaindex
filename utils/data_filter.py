from fastapi import Depends, HTTPException
from schemas.filtrodata_schema import DataFilter
from datetime import datetime, timezone

def get_data_filter(data: DataFilter = Depends()):
    if data.data_inicial is None:
        return None

    if data.data_final is None:
        data.data_final = datetime.now(timezone.utc)
    
    if data.data_final < data.data_inicial:
        raise HTTPException(status_code=400, detail='Data final menor que data inicial')
    
    return data

