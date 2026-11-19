import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import APIRouter, FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from database import engine, LocalSession
from migracoes import aplicar as aplicar_migracoes
from security.settings import settings
from utils.versao_api import API_V1
import models  # registra todos os models no Base
from models import RefreshToken, Convite, AcaoPendente
from routers.auth_routers import auth_router
from routers.usuario_routers import usuario_router, convite_router
from routers.cliente_routers import cliente_router
from routers.empresa_routers import empresa_router
from routers.produto_routers import produto_router
from routers.venda_routers import venda_router
from routers.relatorio_routers import relatorio_router
from routers.previsao_routers import previsao_router
from routers.chat_routers import chat_router
from routers.auditoria_routers import auditoria_router
from routers.painel_routers import painel_router
import services.auditoria_service as auditoria

def limpar_dados_expirados() -> None:
    """Retenção (LGPD): apaga refresh tokens, convites e ações do chat vencidos e a auditoria fora do prazo
    (DELETEs que usam índice: expires_at / (categoria, created_at))."""
    agora = datetime.now(timezone.utc)
    with LocalSession() as db:
        db.query(RefreshToken).filter(RefreshToken.expires_at < agora).delete(synchronize_session=False)
        db.query(Convite).filter(Convite.expires_at < agora).delete(synchronize_session=False)
        db.query(AcaoPendente).filter(AcaoPendente.expires_at < agora).delete(synchronize_session=False)
        auditoria.limpar_vencidos(db, settings.auditoria_retencao_acesso_dias, settings.auditoria_retencao_demais_dias)
        db.commit()

log = logging.getLogger('limpeza')

async def rotina_limpeza(intervalo_horas: float) -> None:
    """Retenção contínua: repete a limpeza a cada `intervalo_horas` enquanto a API estiver no ar.
    Roda numa thread do pool (o DELETE é síncrono) para não travar as requisições. Com vários
    workers, cada um roda a sua: inofensivo, porque o DELETE é idempotente."""
    while True:
        await asyncio.sleep(intervalo_horas * 3600)
        try:
            await run_in_threadpool(limpar_dados_expirados)
        except Exception:
            log.exception('Falha na limpeza agendada de dados expirados')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Estrutura do banco: migrações SQL versionadas (pasta migracoes/), não create_all.
    if settings.migracoes_automaticas:
        aplicar_migracoes(engine)
    limpar_dados_expirados()
    tarefa = asyncio.create_task(rotina_limpeza(settings.limpeza_intervalo_horas))
    yield
    tarefa.cancel()

app = FastAPI(title='Gestão Comercial API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Versionamento da API: tudo sob /api/v1. Mudança incompatível → nova versão (/api/v2) só para as
# rotas afetadas; a v1 continua no ar com os cabeçalhos Deprecation/Sunset até a data de desligamento.
api_v1 = APIRouter(prefix=API_V1)
for router in (auth_router, usuario_router, convite_router, cliente_router, empresa_router, produto_router,
               venda_router, relatorio_router, previsao_router, chat_router, auditoria_router, painel_router):
    api_v1.include_router(router)
app.include_router(api_v1)
