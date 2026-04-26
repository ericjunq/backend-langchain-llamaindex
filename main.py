from fastapi import FastAPI
from database import engine,Base
from routers.usuario_routers import usuario_router

app = FastAPI()
app.include_router(usuario_router)

Base.metadata.create_all(bind=engine)
