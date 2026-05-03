from fastapi import FastAPI
from database import engine,Base
from routers.usuario_routers import usuario_router
from routers.cliente_routers import cliente_router
from routers.empresa_routers import empresa_router
from routers.produto_routers import produto_router
from routers.venda_routers import venda_router
from routers.refresh_token_routers import refresh_token_router

app = FastAPI()
app.include_router(usuario_router)
app.include_router(cliente_router)
app.include_router(empresa_router)
app.include_router(produto_router)
app.include_router(venda_router)
app.include_router(refresh_token_router)

Base.metadata.create_all(bind=engine)