from fastapi import FastAPI
from database import engine,Base
from routers.usuario_routers import usuario_router
from routers.cliente_routers import cliente_router
from routers.empresa_routers import empresa_router

app = FastAPI()
app.include_router(usuario_router)
app.include_router(cliente_router)
app.include_router(empresa_router)

Base.metadata.create_all(bind=engine)
