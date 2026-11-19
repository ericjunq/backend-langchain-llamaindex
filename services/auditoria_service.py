"""Trilha de auditoria.

`registrar()` só faz `db.add()`: o registro entra na MESMA transação da operação. Se ela falhar
(rollback), o log também não fica; se der certo, os dois são gravados juntos. Custo: 1 INSERT.

Origem: 'api' por padrão; o chat marca 'chat' (ContextVar) ao executar uma ação confirmada.
LGPD: em entidades com dado pessoal (usuário, cliente), os campos alterados aparecem só como
"alterado"; senha nunca aparece; IP só em eventos de acesso.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from models.auditoria_model import Auditoria
from models.usuario_model import Usuarios

ACESSO, OPERACAO, VENDA = 'acesso', 'operacao', 'venda'

_origem: ContextVar[str] = ContextVar('origem_auditoria', default='api')

CAMPOS_PESSOAIS = {'nome', 'sobrenome', 'email', 'cpf', 'telefone'}
CAMPOS_SECRETOS = {'senha', 'senha_hash', 'senha_atual'}


@contextmanager
def origem(valor: str):
    token = _origem.set(valor)
    try:
        yield
    finally:
        _origem.reset(token)


def campos_alterados(campos: dict, pessoais: bool = False) -> dict:
    """{'preco_venda': 30} fica como está; em entidades pessoais, {'email': 'x'} → {'email': 'alterado'}."""
    resultado = {}
    for campo, valor in campos.items():
        if campo in CAMPOS_SECRETOS or (pessoais and campo in CAMPOS_PESSOAIS):
            resultado[campo] = 'alterado'
        else:
            resultado[campo] = valor
    return resultado


def registrar(db: Session, acao: str, *, usuario: Optional[Usuarios] = None, empresa_id: Optional[int] = None,
              entidade: Optional[str] = None, entidade_id=None, detalhes: Optional[dict] = None,
              categoria: str = OPERACAO, ip: Optional[str] = None) -> None:
    db.add(Auditoria(
        empresa_id=empresa_id if empresa_id is not None else (usuario.empresa_id if usuario else None),
        usuario_id=usuario.id if usuario else None,
        categoria=categoria,
        acao=acao,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else None,
        origem=_origem.get(),
        # Decimal vira texto ("30.00"): dinheiro na auditoria fica exato, sem arredondamento de float.
        detalhes=jsonable_encoder(detalhes, custom_encoder={Decimal: str}) if detalhes else None,
        ip=ip if categoria == ACESSO else None,
    ))


def limpar_vencidos(db: Session, dias_acesso: int, dias_demais: int) -> None:
    """Retenção: 2 DELETEs usando o índice (categoria, created_at). Sem commit."""
    agora = datetime.now(timezone.utc)
    db.query(Auditoria).filter(Auditoria.categoria == ACESSO,
                               Auditoria.created_at < agora - timedelta(days=dias_acesso)
                               ).delete(synchronize_session=False)
    db.query(Auditoria).filter(Auditoria.categoria.in_([OPERACAO, VENDA]),
                               Auditoria.created_at < agora - timedelta(days=dias_demais)
                               ).delete(synchronize_session=False)


def listar(db: Session, usuario: Usuarios, filtro, paginacao, intervalo=None) -> list[dict]:
    """GET /auditoria (só o dono, só a própria empresa). 1 consulta com join para o nome de quem fez."""
    from security.permissoes import exigir_cargo
    from utils.data_filter import filtros_intervalo
    from utils.enums import CargosEnum
    exigir_cargo(usuario, CargosEnum.dono, detail='Só o dono consulta a auditoria')

    query = (
        db.query(Auditoria, Usuarios.nome)
        .outerjoin(Usuarios, Usuarios.id == Auditoria.usuario_id)
        .filter(Auditoria.empresa_id == usuario.empresa_id, *filtros_intervalo(Auditoria.created_at, intervalo))
    )
    for campo in ('categoria', 'acao', 'entidade', 'entidade_id', 'usuario_id', 'origem'):
        valor = getattr(filtro, campo)
        if valor is not None:
            query = query.filter(getattr(Auditoria, campo) == (str(valor) if campo == 'entidade_id' else valor))

    linhas = paginacao.aplicar(query.order_by(Auditoria.created_at.desc(), Auditoria.id.desc())).all()
    # IP fica fora da resposta (mínima exposição): guardado só para investigação de segurança.
    return [{
        'id': a.id, 'quando': a.created_at, 'usuario_id': a.usuario_id, 'usuario': nome,
        'categoria': a.categoria, 'acao': a.acao, 'entidade': a.entidade, 'entidade_id': a.entidade_id,
        'origem': a.origem, 'detalhes': a.detalhes,
    } for a, nome in linhas]
