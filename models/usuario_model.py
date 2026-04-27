from sqlalchemy import Column, UniqueConstraint, func, ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from database import Base
from utils.enums import CargosEnum
from sqlalchemy import Enum as SAEnum
from models.empresa_model import Empresa
from models.cliente_model import Clientes

class Usuarios(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, autoincrement=True, primary_key=True)
    nome = Column(String(30), nullable=False)
    sobrenome = Column(String(50), nullable=False)
    email = Column(String(60), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    cpf = Column(String(11), nullable=False)
    telefone = Column(String(11), nullable=False)
    cargo = Column(SAEnum(CargosEnum))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(Boolean, default=True, nullable=False)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True)

    empresa = relationship("Empresa", back_populates='usuarios')
    cliente = relationship("Clientes", back_populates='usuario')

    __table_args__=(
        UniqueConstraint('empresa_id', 'email', name='uq_usuario_email_empresa'),
        UniqueConstraint('empresa_id', 'telefone', name='uq_usuario_tel_empresa'),
        UniqueConstraint('empresa_id', 'cpf', name='uq_usuario_cpf_empresa'),
    )

