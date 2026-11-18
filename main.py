from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, LocalSession
from security.settings import settings
import models  # registra todos os models no Base
from models import RefreshToken, Convite
from routers.auth_routers import auth_router
from routers.usuario_routers import usuario_router, convite_router
from routers.cliente_routers import cliente_router
from routers.empresa_routers import empresa_router
from routers.produto_routers import produto_router
from routers.venda_routers import venda_router
from routers.relatorio_routers import relatorio_router
from routers.previsao_routers import previsao_router

def limpar_dados_expirados() -> None:
    """Retenção (LGPD): apaga refresh tokens e convites vencidos. 2 DELETEs usando índice em expires_at."""
    agora = datetime.now(timezone.utc)
    with LocalSession() as db:
        db.query(RefreshToken).filter(RefreshToken.expires_at < agora).delete(synchronize_session=False)
        db.query(Convite).filter(Convite.expires_at < agora).delete(synchronize_session=False)
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sem migrações: a estrutura vem dos models. Mudou model → recriar o banco (ver CLAUDE.md).
    Base.metadata.create_all(bind=engine)
    limpar_dados_expirados()
    yield

app = FastAPI(title='Gestão Comercial API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth_router)
app.include_router(usuario_router)
app.include_router(convite_router)
app.include_router(cliente_router)
app.include_router(empresa_router)
app.include_router(produto_router)
app.include_router(venda_router)
app.include_router(relatorio_router)
app.include_router(previsao_router)
