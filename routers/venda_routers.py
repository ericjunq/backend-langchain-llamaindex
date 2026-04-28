from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas.cliente_schema import ClienteCreate, ClienteResponse, ClienteUpdate
from security.dependencies import get_db
from models.empresa_model import Empresa
from models.cliente_model import Clientes
from models.usuario_model import Usuarios
from models.vendas_model import Vendas
from security.security import get_current_user