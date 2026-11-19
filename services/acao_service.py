"""Ações propostas pelo assistente: criar (pendente), confirmar e cancelar.

A execução NÃO passa pelo modelo de linguagem: a rota de confirmação chama o service
diretamente com os dados guardados. Uma interpretação errada do modelo nunca altera
dados sem o "sim" explícito do usuário.
"""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.acao_pendente import AcaoPendente
from models.usuario_model import Usuarios
from schemas.produto_schema import ProdutoReposicaoEstoque, ProdutoResponse
from schemas.venda_schema import VendaResponse, VendaSchema
import services.produto_service as produto_service
import services.venda_service as venda_service
import services.auditoria_service as auditoria

REGISTRAR_VENDA = 'registrar_venda'
REPOR_ESTOQUE = 'repor_estoque'


def criar(db: Session, usuario: Usuarios, tipo: str, dados: dict, resumo: str) -> AcaoPendente:
    acao = AcaoPendente(usuario_id=usuario.id, empresa_id=usuario.empresa_id, tipo=tipo, dados=dados, resumo=resumo)
    db.add(acao)
    db.commit()
    db.refresh(acao)
    return acao


def _buscar(db: Session, usuario: Usuarios, id: str) -> AcaoPendente:
    # FOR UPDATE: dois cliques em "confirmar" ao mesmo tempo → o segundo espera e não acha mais a ação.
    acao = db.query(AcaoPendente).filter(
        AcaoPendente.id == id,
        AcaoPendente.usuario_id == usuario.id,  # só quem pediu pode confirmar
    ).with_for_update().first()
    if acao is None:
        raise HTTPException(status_code=404, detail='Ação não encontrada')

    expira = acao.expires_at if acao.expires_at.tzinfo else acao.expires_at.replace(tzinfo=timezone.utc)
    if expira <= datetime.now(timezone.utc):
        db.delete(acao)
        db.commit()
        raise HTTPException(status_code=410, detail='Ação expirada: peça novamente ao assistente')
    return acao


def confirmar(db: Session, usuario: Usuarios, id: str) -> dict:
    acao = _buscar(db, usuario, id)
    tipo, dados = acao.tipo, acao.dados

    # A ação é apagada na MESMA transação do service: se ele falhar (ex.: estoque mudou),
    # o rollback mantém a ação; se der certo, ela some junto com o commit (não executa duas vezes).
    db.delete(acao)
    db.flush()

    with auditoria.origem('chat'):
        if tipo == REGISTRAR_VENDA:
            venda = venda_service.criar_venda(VendaSchema(**dados), db, usuario)
            resultado = VendaResponse.model_validate(venda, from_attributes=True)
        elif tipo == REPOR_ESTOQUE:
            produto = produto_service.repor_estoque(
                dados['produto_id'], ProdutoReposicaoEstoque(quantidade=dados['quantidade']), db, usuario)
            resultado = ProdutoResponse.model_validate(produto, from_attributes=True)
        else:
            raise HTTPException(status_code=400, detail='Tipo de ação desconhecido')

    return {'tipo': tipo, 'resultado': resultado.model_dump(mode='json')}


def cancelar(db: Session, usuario: Usuarios, id: str) -> None:
    acao = db.query(AcaoPendente).filter(AcaoPendente.id == id, AcaoPendente.usuario_id == usuario.id).first()
    if acao is None:
        raise HTTPException(status_code=404, detail='Ação não encontrada')
    db.delete(acao)
    db.commit()
