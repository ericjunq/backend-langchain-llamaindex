"""Ferramentas do assistente.

Cada ferramenta:
  - chama os services que já existem COM o usuário logado → permissões e isolamento
    entre empresas valem também no chat;
  - devolve JSON COMPACTO: só os campos necessários, chaves curtas, sem espaços, máx. 10 itens.
    Cada item é um objeto com chaves (não "colunas + linhas"): no teste com o qwen3:8b o
    formato em colunas fez o modelo desalinhar valores ("comprar 1" em vez de 4);
  - LGPD: nunca entrega CPF, email ou telefone; clientes aparecem como "Nome S.".
"""
import json
from typing import Literal, Optional

from fastapi import HTTPException
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.cliente_model import Clientes
from models.usuario_model import Usuarios
from schemas.cliente_schema import FiltrarCliente
from schemas.produto_schema import FiltrarProdutos
from schemas.venda_schema import FiltroVendas
from utils.data_filter import IntervaloData, inicio_do_periodo
from utils.enums import PeriodoEnum
from utils.paginacao import Paginacao
import services.cliente_service as cliente_service
import services.previsao_service as previsao_service
import services.produto_service as produto_service
import services.relatorio_service as relatorio_service
import services.venda_service as venda_service

LIMITE = 10


def compactar(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, separators=(',', ':'), default=str)


def nome_curto(nome: Optional[str]) -> Optional[str]:
    """'Maria Souza Lima' → 'Maria S.' (mínima exposição)."""
    if not nome:
        return None
    partes = nome.split()
    return partes[0] if len(partes) == 1 else f'{partes[0]} {partes[1][0]}.'


def _intervalo(periodo: Optional[str]) -> Optional[IntervaloData]:
    if not periodo:
        return None
    from datetime import datetime, timezone
    return IntervaloData(inicio=inicio_do_periodo(PeriodoEnum(periodo), datetime.now(timezone.utc)))


Periodo = Optional[Literal['mes', 'semestre', 'ano']]

# --- Argumentos (o schema vira a descrição que o modelo recebe) ---

class ArgsBuscarProdutos(BaseModel):
    nome: Optional[str] = Field(None, description='Parte do nome do produto (sem acento ou maiúscula, tanto faz)')
    abaixo_estoque_min: bool = Field(False, description='Só produtos com estoque igual ou abaixo do mínimo')

class ArgsPrever(BaseModel):
    produto_id: int = Field(description='Id do produto (use buscar_produtos para descobrir)')
    dias: int = Field(30, ge=1, le=180, description='Horizonte da previsão em dias')

class ArgsReposicao(BaseModel):
    prazo_entrega: int = Field(7, ge=0, le=90, description='Dias até o fornecedor entregar')
    dias_cobertura: int = Field(30, ge=1, le=180, description='Por quantos dias a compra deve durar')

class ArgsPeriodo(BaseModel):
    periodo: Periodo = Field(None, description='mes, semestre ou ano corrente; vazio = todo o histórico')

class ArgsUltimasVendas(BaseModel):
    quantidade: int = Field(5, ge=1, le=LIMITE)

class ArgsBuscarClientes(BaseModel):
    nome: str = Field(min_length=2, description='Parte do nome do cliente')


def criar_ferramentas_leitura(db: Session, usuario: Usuarios) -> list[StructuredTool]:

    def buscar_produtos(nome: Optional[str] = None, abaixo_estoque_min: bool = False) -> str:
        produtos = produto_service.listar_produtos(
            FiltrarProdutos(nome=nome, abaixo_estoque_min=abaixo_estoque_min),
            Paginacao(LIMITE, 0), db, usuario)
        return compactar([
            {'id': p.id, 'produto': p.nome, 'estoque': p.quantidade, 'estoque_min': p.estoque_min,
             'preco_venda': float(p.preco_venda)}
            for p in produtos])

    def prever_demanda(produto_id: int, dias: int = 30) -> str:
        p = previsao_service.prever_produto(db, usuario, produto_id, dias)
        return compactar({
            'produto': p['produto'], 'estoque': p['estoque_atual'], 'dias': dias,
            'demanda_prevista': p['demanda_prevista'], 'faixa_80': list(p['intervalo_80'].values()),
            'acaba_em': p['data_ruptura_estimada'], 'tendencia_pct': p['tendencia_pct'],
            'confianca': p['confianca'],
        })

    def sugerir_reposicao(prazo_entrega: int = 7, dias_cobertura: int = 30) -> str:
        r = previsao_service.sugerir_reposicao(db, usuario, prazo_entrega, dias_cobertura, True)
        grupos = {}
        for nivel in ('comprar_agora', 'em_breve'):
            grupos[nivel] = [
                {'produto': i['produto'], 'estoque': i['estoque_atual'], 'comprar': i['quantidade_sugerida'],
                 'confianca': i['confianca'],
                 # sem previsão de ruptura (sem vendas): o campo é omitido para o modelo não inventar data
                 **({'acaba_em': i['data_ruptura_estimada']} if i['data_ruptura_estimada'] else {})}
                for i in r['itens'] if i['necessidade'] == nivel
            ][:LIMITE]
        return compactar({
            'por_necessidade': r['resumo']['por_necessidade'],
            **grupos,
            'gasto_estimado_reposicao': r['resumo']['gasto_estimado_reposicao'],
            'obs': 'gasto é ESTIMADO com o preço de compra atual',
        })

    def resumo_vendas(periodo: Periodo = None) -> str:
        r = relatorio_service.relatorio_vendas(db, usuario, _intervalo(periodo))
        return compactar({
            'periodo': periodo or 'todo o histórico', **r['resumo'],
            'top_produtos': [{'produto': x['produto'], 'vendido': x['quantidade']}
                             for x in r['produtos_mais_vendidos'][:3]],
        })

    def resumo_produtos(periodo: Periodo = None) -> str:
        r = relatorio_service.relatorio_produtos(db, usuario, _intervalo(periodo))
        return compactar({
            'periodo': periodo or 'todo o histórico', **r['resumo'],
            'mais_vendidos': [{'produto': x['produto'], 'vendido': x['vendido']} for x in r['mais_vendidos'][:5]],
            'sem_venda': [x['produto'] for x in r['sem_venda'][:5]],
        })

    def ultimas_vendas(quantidade: int = 5) -> str:
        vendas = venda_service.listar_vendas(FiltroVendas(), db, usuario, Paginacao(quantidade, 0))
        ids = {v.cliente_id for v in vendas if v.cliente_id}
        nomes = dict(db.query(Clientes.id, Clientes.nome).filter(Clientes.id.in_(ids)).all()) if ids else {}
        return compactar([
            {'id': v.id, 'data': v.created_at.date(), 'valor': float(v.valor_final),
             'pagamento': v.forma_pagamento.value, 'status': v.status.value,
             'cliente': nome_curto(nomes.get(v.cliente_id))}
            for v in vendas])

    def buscar_clientes(nome: str) -> str:
        clientes = cliente_service.listar_clientes(db, usuario, Paginacao(LIMITE, 0), filtro=FiltrarCliente(nome=nome))
        return compactar([{'id': c.id, 'cliente': nome_curto(c.nome)} for c in clientes])

    def ferramenta(func, args, descricao):
        return StructuredTool.from_function(func=func, name=func.__name__, description=descricao, args_schema=args)

    return [
        ferramenta(buscar_produtos, ArgsBuscarProdutos,
                   'Busca produtos ativos por nome e/ou os que estão abaixo do estoque mínimo. Devolve id, estoque e preço.'),
        ferramenta(prever_demanda, ArgsPrever,
                   'Previsão de demanda de UM produto: quantidade prevista, faixa provável, quando o estoque acaba e confiança.'),
        ferramenta(sugerir_reposicao, ArgsReposicao,
                   'O que precisa ser comprado: produtos por nível de necessidade (comprar_agora, em_breve), '
                   'quanto comprar e gasto ESTIMADO.'),
        ferramenta(resumo_vendas, ArgsPeriodo,
                   'Resumo de vendas: total, canceladas, ticket médio, faturamento e produtos mais vendidos.'),
        ferramenta(resumo_produtos, ArgsPeriodo,
                   'Resumo do estoque: valor em estoque, margem, produtos abaixo do mínimo e sem venda.'),
        ferramenta(ultimas_vendas, ArgsUltimasVendas, 'Últimas vendas registradas (as mais recentes primeiro).'),
        ferramenta(buscar_clientes, ArgsBuscarClientes, 'Busca clientes pelo nome. Devolve id e nome abreviado.'),
    ]


def executar_ferramenta(ferramenta: StructuredTool, argumentos: dict) -> str:
    """Erros de negócio e de validação viram texto para o modelo explicar ao usuário (sem derrubar o chat)."""
    try:
        return ferramenta.invoke(argumentos)
    except HTTPException as e:
        return compactar({'erro': e.detail})
    except Exception as e:  # argumentos inválidos gerados pelo modelo, etc.
        return compactar({'erro': f'Não foi possível executar {ferramenta.name}: {type(e).__name__}'})
