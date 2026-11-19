from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, func
from database import Base


class Auditoria(Base):
    """Trilha de auditoria: quem fez o quê, quando e por onde (api/chat). Só recebe INSERT
    (nenhuma rota edita ou apaga); a retenção apaga o que venceu. Também é dado pessoal (LGPD):
    campos pessoais alterados aparecem só como "alterado", nunca com o valor."""
    __tablename__ = 'auditoria'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True, index=True)
    categoria = Column(String(10), nullable=False)       # acesso | operacao | venda (define a retenção)
    acao = Column(String(40), nullable=False)            # ex.: produto.editado, venda.cancelada, login
    entidade = Column(String(30), nullable=True)
    entidade_id = Column(String(36), nullable=True)
    origem = Column(String(10), nullable=False, server_default='api')   # api | chat
    detalhes = Column(JSON, nullable=True)
    ip = Column(String(45), nullable=True)               # só em eventos de acesso (segurança)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index('ix_auditoria_empresa_created', 'empresa_id', 'created_at'),     # consulta do dono
        Index('ix_auditoria_entidade', 'entidade', 'entidade_id'),             # histórico de um registro
        Index('ix_auditoria_categoria_created', 'categoria', 'created_at'),    # retenção
    )
