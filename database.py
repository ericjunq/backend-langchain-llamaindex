from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from security.settings import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(
    settings.database_url
)

LocalSession = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)