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

# --- Produto e cliente por NOME (não por id) ---
# No teste real, o qwen3:8b inventou um id em vez de buscar antes. As ferramentas recebem o nome
# como o usuário falou e resolvem aqui; se for ambíguo, devolvem as opções para o modelo perguntar.

def resolver_produto(db: Session, usuario: Usuarios, referencia: str):
    from utils.normalizar_nome import normalizar_nome
    ref = (referencia or '').strip()
    if not ref:
        raise HTTPException(status_code=400, detail='Informe o nome do produto')

    if ref.upper().startswith('PROD-'):
        candidatos = produto_service.listar_produtos(FiltrarProdutos(codigo_produto=ref), Paginacao(2, 0), db, usuario)
    else:
        candidatos = produto_service.listar_produtos(FiltrarProdutos(nome=ref), Paginacao(LIMITE, 0), db, usuario)
        exatos = [p for p in candidatos if p.nome_normalizado == normalizar_nome(ref)]
        if len(exatos) == 1:
            return exatos[0]

    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        raise HTTPException(status_code=404, detail=f'Produto "{ref}" não encontrado')
    raise HTTPException(status_code=409, detail=f'Mais de um produto corresponde a "{ref}": '
                        f'{", ".join(p.nome for p in candidatos)}. Pergunte ao usuário qual.')


def resolver_cliente(db: Session, usuario: Usuarios, referencia: str):
    ref = (referencia or '').strip()
    candidatos = cliente_service.listar_clientes(db, usuario, Paginacao(LIMITE, 0), filtro=FiltrarCliente(nome=ref))
    exatos = [c for c in candidatos if c.nome.strip().lower() == ref.lower()]
    if len(exatos) == 1:
        return exatos[0]
    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        raise HTTPException(status_code=404, detail=f'Cliente "{ref}" não encontrado')
    raise HTTPException(status_code=409, detail=f'Mais de um cliente corresponde a "{ref}": '
                        f'{", ".join(nome_curto(c.nome) for c in candidatos)}. Pergunte ao usuário qual.')

# --- Argumentos (o schema vira a descrição que o modelo recebe) ---

class ArgsBuscarProdutos(BaseModel):
    nome: Optional[str] = Field(None, description='Parte do nome do produto (sem acento ou maiúscula, tanto faz)')
    abaixo_estoque_min: bool = Field(False, description='Só produtos com estoque igual ou abaixo do mínimo')

class ArgsPrever(BaseModel):
    produto: str = Field(description='Nome (ou código PROD-...) do produto, como o usuário falou')
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
            {'produto': p.nome, 'codigo': p.codigo_produto, 'estoque': p.quantidade, 'estoque_min': p.estoque_min,
             'preco_venda': float(p.preco_venda)}
            for p in produtos])

    def prever_demanda(produto: str, dias: int = 30) -> str:
        p = previsao_service.prever_produto(db, usuario, resolver_produto(db, usuario, produto).id, dias)
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
        return compactar([nome_curto(c.nome) for c in clientes])

    def ferramenta(func, args, descricao):
        return StructuredTool.from_function(func=func, name=func.__name__, description=descricao, args_schema=args)

    return [
        ferramenta(buscar_produtos, ArgsBuscarProdutos,
                   'Busca produtos ativos por nome e/ou os que estão abaixo do estoque mínimo. Devolve estoque e preço.'),
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
        ferramenta(buscar_clientes, ArgsBuscarClientes, 'Busca clientes pelo nome. Devolve os nomes abreviados.'),
    ]


def executar_ferramenta(ferramenta: StructuredTool, argumentos: dict) -> str:
    """Erros de negócio e de validação viram texto para o modelo explicar ao usuário (sem derrubar o chat)."""
    try:
        return ferramenta.invoke(argumentos)
    except HTTPException as e:
        return compactar({'erro': e.detail})
    except Exception as e:  # argumentos inválidos gerados pelo modelo, etc.
        return compactar({'erro': f'Não foi possível executar {ferramenta.name}: {type(e).__name__}'})


# ============================ Ferramentas de escrita ============================
# Não executam nada: validam, montam um resumo legível e criam uma AÇÃO PENDENTE.
# Quem executa é a rota POST /chat/acoes/{id}/confirmar, depois do "sim" do usuário.

class ArgsItemVenda(BaseModel):
    produto: str = Field(description='Nome (ou código PROD-...) do produto, como o usuário falou')
    quantidade: int = Field(gt=0)

class ArgsRegistrarVenda(BaseModel):
    itens: list[ArgsItemVenda] = Field(min_length=1)
    forma_pagamento: Literal['pix', 'cartao_credito', 'cartao_debito', 'boleto', 'dinheiro']
    cliente: Optional[str] = Field(None, description='Nome do cliente, se o usuário informou; vazio = sem cliente')
    desconto: float = Field(0, ge=0, description='Desconto em reais sobre o total')

class ArgsReporEstoque(BaseModel):
    produto: str = Field(description='Nome (ou código PROD-...) do produto, como o usuário falou')
    quantidade: int = Field(gt=0, description='Unidades que chegaram (somam ao estoque)')

class ArgsCancelarVenda(BaseModel):
    venda_id: int = Field(description='Número da venda (use ultimas_vendas para encontrar)')
    motivo: str = Field(min_length=3, max_length=60,
                        description='Motivo do cancelamento, dito pelo usuário. OBRIGATÓRIO: se ele não disse, pergunte.')


def _reais(valor) -> str:
    return f'R$ {float(valor):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def criar_ferramentas_escrita(db: Session, usuario: Usuarios, pendentes: list) -> list[StructuredTool]:
    from decimal import Decimal
    import services.acao_service as acao_service
    from schemas.venda_schema import VendaSchema
    from security.permissoes import GESTORES, exigir_cargo

    def _pendente(tipo: str, dados: dict, resumo: str) -> str:
        acao = acao_service.criar(db, usuario, tipo, dados, resumo)
        pendentes.append(acao)
        return compactar({'acao_pendente': acao.id, 'resumo': resumo,
                          'situacao': 'NÃO executado: o usuário precisa clicar em Confirmar'})

    def registrar_venda(itens: list, forma_pagamento: str, cliente: Optional[str] = None, desconto: float = 0) -> str:
        itens = [i if isinstance(i, dict) else i.model_dump() for i in itens]
        produtos = {}
        for i in itens:
            produto = resolver_produto(db, usuario, i['produto'])
            produtos[produto.id] = produto
            i['produto_id'] = produto.id
        cliente_obj = resolver_cliente(db, usuario, cliente) if cliente else None

        venda = VendaSchema(
            descricao='Venda registrada pelo assistente', forma_pagamento=forma_pagamento,
            cliente_id=cliente_obj.id if cliente_obj else None, desconto=Decimal(str(desconto)),
            itens=[{'produto_id': i['produto_id'], 'quantidade': i['quantidade']} for i in itens])

        # Prévia (sem travar estoque): a validação definitiva acontece na confirmação.
        linhas, total = [], Decimal('0')
        for item in venda.itens:
            produto = produtos[item.produto_id]
            if produto.quantidade < item.quantidade:
                return compactar({'erro': f'Estoque insuficiente de {produto.nome}: há {produto.quantidade}'})
            subtotal = produto.preco_venda * item.quantidade
            total += subtotal
            linhas.append(f'{item.quantidade}× {produto.nome} ({_reais(subtotal)})')
        if venda.desconto > total:
            return compactar({'erro': 'Desconto maior que o valor da venda'})

        partes = [f"Venda: {', '.join(linhas)}", forma_pagamento]
        if cliente_obj:
            partes.append(f'cliente {nome_curto(cliente_obj.nome)}')
        if venda.desconto:
            partes.append(f'desconto {_reais(venda.desconto)}')
        partes.append(f'total {_reais(total - venda.desconto)}')
        return _pendente(acao_service.REGISTRAR_VENDA, venda.model_dump(mode='json'), ' · '.join(partes))

    def repor_estoque(produto: str, quantidade: int) -> str:
        exigir_cargo(usuario, *GESTORES, detail='Você não tem permissão para repor estoque')
        alvo = resolver_produto(db, usuario, produto)
        resumo = (f'Repor estoque: +{quantidade} × {alvo.nome} '
                  f'(estoque {alvo.quantidade} → {alvo.quantidade + quantidade})')
        return _pendente(acao_service.REPOR_ESTOQUE, {'produto_id': alvo.id, 'quantidade': quantidade}, resumo)

    def cancelar_venda(venda_id: int, motivo: str) -> str:
        from models.produto_model import Produtos
        from utils.enums import StatusVenda
        # Mesmas regras da API (empresa, funcionário só as próprias) já na preparação.
        venda = venda_service.obter_venda(venda_id, db, usuario)
        if venda.status == StatusVenda.cancelada:
            return compactar({'erro': f'A venda {venda_id} já está cancelada'})
        nomes = dict(db.query(Produtos.id, Produtos.nome)
                     .filter(Produtos.id.in_([i.produto_id for i in venda.itens])).all())
        itens = ', '.join(f'{i.quantidade}× {nomes.get(i.produto_id, "?")}' for i in venda.itens)
        resumo = (f'Cancelar venda #{venda.id} ({itens} · {_reais(venda.valor_final)} · '
                  f'{venda.created_at:%d/%m/%Y}) · motivo: {motivo.strip()} · o estoque será devolvido')
        return _pendente(acao_service.CANCELAR_VENDA, {'venda_id': venda.id, 'motivo': motivo.strip()}, resumo)

    return [
        StructuredTool.from_function(
            func=registrar_venda, name='registrar_venda', args_schema=ArgsRegistrarVenda,
            description='PREPARA uma venda para o usuário confirmar (não executa). '
                        'Use os nomes dos produtos e do cliente como o usuário falou.'),
        StructuredTool.from_function(
            func=repor_estoque, name='repor_estoque', args_schema=ArgsReporEstoque,
            description='PREPARA uma entrada de estoque para o usuário confirmar (não executa).'),
        StructuredTool.from_function(
            func=cancelar_venda, name='cancelar_venda', args_schema=ArgsCancelarVenda,
            description='PREPARA o cancelamento de uma venda para o usuário confirmar (não executa). '
                        'Exige o motivo dito pelo usuário; se faltar, pergunte antes de chamar.'),
    ]
