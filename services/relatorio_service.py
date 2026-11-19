from datetime import datetime, timezone
from io import BytesIO
from typing import Optional
import pandas as pd
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from models.cliente_model import Clientes
from models.produto_model import Produtos
from models.vendas_model import Vendas, ItemVendas
from models.usuario_model import Usuarios
from security.permissoes import exigir_cargo, GESTORES
from utils.enums import CargosEnum, StatusVenda
from utils.data_filter import IntervaloData, filtros_intervalo
import services.auditoria_service as auditoria

TOP_N = 5
TOP_N_PRODUTOS = 10

# --- Utilitários ---

def _registros(df: pd.DataFrame) -> list:
    """DataFrame → lista de dicts, trocando NaN por None (NaN não é JSON válido)."""
    return df.astype(object).where(df.notna(), None).to_dict(orient='records')

def _ranking(df: pd.DataFrame, coluna: str, maiores: bool, n: int = TOP_N) -> list:
    if df.empty:
        return []
    escolhidos = df.nlargest(n, coluna) if maiores else df.nsmallest(n, coluna)
    return _registros(escolhidos)

def _excel(abas: dict) -> bytes:
    """Gera o .xlsx em memória: nada fica salvo no disco do servidor (LGPD)."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for nome, dados in abas.items():
            df = dados if isinstance(dados, pd.DataFrame) else pd.DataFrame(dados)
            df.to_excel(writer, sheet_name=nome, index=False)
    return buffer.getvalue()

def _filtros_vendas(usuario: Usuarios, intervalo: Optional[IntervaloData]) -> list:
    return [Vendas.empresa_id == usuario.empresa_id, *filtros_intervalo(Vendas.created_at, intervalo)]

CONCLUIDA = Vendas.status != StatusVenda.cancelada


def _registrar_exportacao(db: Session, usuario: Usuarios, relatorio: str, intervalo: Optional[IntervaloData]) -> None:
    """Exportar é tirar dados (inclusive pessoais) do sistema em massa: fica na auditoria (LGPD)."""
    periodo = None
    if intervalo:
        periodo = {'inicio': intervalo.inicio, 'fim': intervalo.fim}
    auditoria.registrar(db, 'relatorio.exportado', usuario=usuario, categoria=auditoria.ACESSO,
                        detalhes={'relatorio': relatorio, 'periodo': periodo})
    db.commit()

# =========================== Relatório de vendas ===========================

def _dados_relatorio_vendas(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData]):
    """4 consultas no total: 1 de resumo + 1 agregada por entidade (produto, funcionário, cliente).
    Os rankings (top/bottom 5) saem do mesmo resultado em memória, em vez de 1 consulta por ranking."""
    exigir_cargo(usuario, CargosEnum.dono)

    filtros = _filtros_vendas(usuario, intervalo)

    total, canceladas, clientes_distintos, faturamento = db.query(
        func.count(Vendas.id),
        func.count(Vendas.id).filter(Vendas.status == StatusVenda.cancelada),
        func.count(func.distinct(Vendas.cliente_id)).filter(CONCLUIDA),
        func.coalesce(func.sum(Vendas.valor_final).filter(CONCLUIDA), 0),
    ).filter(*filtros).one()

    concluidas = total - canceladas
    faturamento = float(faturamento)

    resumo = {
        'total_vendas': total,
        'total_vendas_canceladas': canceladas,
        'taxa_cancelamento': round(canceladas / total, 4) if total else 0,
        'total_clientes': clientes_distintos,
        'ticket_medio': round(faturamento / concluidas, 2) if concluidas else 0,
        'faturamento_total': round(faturamento, 2),
    }

    produtos = pd.DataFrame(
        db.query(Produtos.nome, func.sum(ItemVendas.quantidade), func.sum(ItemVendas.subtotal))
        .join(ItemVendas, ItemVendas.produto_id == Produtos.id)
        .join(Vendas, Vendas.id == ItemVendas.venda_id)
        .filter(*filtros, CONCLUIDA)
        .group_by(Produtos.id, Produtos.nome)
        .all(),
        columns=['produto', 'quantidade', 'valor_total'],
    )

    funcionarios = pd.DataFrame(
        db.query(Usuarios.nome, func.count(Vendas.id), func.sum(Vendas.valor_final))
        .join(Vendas, Vendas.usuario_id == Usuarios.id)
        .filter(*filtros, CONCLUIDA)
        .group_by(Usuarios.id, Usuarios.nome)
        .all(),
        columns=['nome', 'quantidade', 'valor_total'],
    )

    clientes = pd.DataFrame(
        db.query(Clientes.nome, func.count(Vendas.id), func.sum(Vendas.valor_final))
        .join(Vendas, Vendas.cliente_id == Clientes.id)
        .filter(*filtros, CONCLUIDA)
        .group_by(Clientes.id, Clientes.nome)
        .all(),
        columns=['nome', 'quantidade', 'valor_total'],
    )

    # Numeric chega como Decimal; o pandas só ordena/rankeia com tipo numérico.
    for df in (produtos, funcionarios, clientes):
        df['quantidade'] = df['quantidade'].astype(int)
        df['valor_total'] = df['valor_total'].astype(float).round(2)

    rankings = {
        'produtos_mais_vendidos': _ranking(produtos[['produto', 'quantidade']], 'quantidade', True),
        'produtos_menos_vendidos': _ranking(produtos[['produto', 'quantidade']], 'quantidade', False),
        'produtos_maior_faturamento': _ranking(produtos[['produto', 'valor_total']], 'valor_total', True),
        'produtos_menor_faturamento': _ranking(produtos[['produto', 'valor_total']], 'valor_total', False),
        'funcionarios_mais_vendas': _ranking(funcionarios[['nome', 'quantidade']], 'quantidade', True),
        'funcionarios_menos_vendas': _ranking(funcionarios[['nome', 'quantidade']], 'quantidade', False),
        'funcionarios_maior_faturamento': _ranking(funcionarios[['nome', 'valor_total']], 'valor_total', True),
        'funcionarios_menor_faturamento': _ranking(funcionarios[['nome', 'valor_total']], 'valor_total', False),
        'clientes_mais_compras': _ranking(clientes[['nome', 'quantidade']], 'quantidade', True),
        'clientes_maior_faturamento': _ranking(clientes[['nome', 'valor_total']], 'valor_total', True),
    }

    return resumo, rankings

def relatorio_vendas(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData] = None) -> dict:
    resumo, rankings = _dados_relatorio_vendas(db, usuario, intervalo)
    return {'resumo': resumo, **rankings}

ABAS_VENDAS = {
    'produtos_mais_vendidos': 'Prod Mais Vendidos',
    'produtos_menos_vendidos': 'Prod Menos Vendidos',
    'produtos_maior_faturamento': 'Prod Maior Fat',
    'produtos_menor_faturamento': 'Prod Menor Fat',
    'funcionarios_mais_vendas': 'Func Mais Vendas',
    'funcionarios_menos_vendas': 'Func Menos Vendas',
    'funcionarios_maior_faturamento': 'Func Maior Fat',
    'funcionarios_menor_faturamento': 'Func Menor Fat',
    'clientes_mais_compras': 'Clientes Mais Compras',
    'clientes_maior_faturamento': 'Clientes Maior Fat',
}

def exportar_relatorio_vendas(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData] = None) -> bytes:
    resumo, rankings = _dados_relatorio_vendas(db, usuario, intervalo)
    _registrar_exportacao(db, usuario, 'vendas', intervalo)
    return _excel({'Resumo': [resumo], **{aba: rankings[chave] for chave, aba in ABAS_VENDAS.items()}})

# ========================== Relatório de produtos ==========================

COLUNAS_PRODUTOS = ['produto', 'codigo', 'ativo', 'estoque', 'estoque_min', 'preco_compra', 'preco_venda',
                    'vendido', 'faturamento', 'custo', 'primeira_venda']

def _dados_relatorio_produtos(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData]):
    """1 consulta: produtos ativos LEFT JOIN vendas concluídas do período (agregadas por produto).
    Inclui produtos desativados que venderam no período (o faturamento bate com o relatório de vendas).
    Resumo, margens, giro, produtos sem venda e reposição saem do mesmo resultado, em memória."""
    exigir_cargo(usuario, *GESTORES)

    vendido = (
        db.query(
            ItemVendas.produto_id.label('produto_id'),
            func.sum(ItemVendas.quantidade).label('qtd'),
            func.sum(ItemVendas.subtotal).label('fat'),
            func.sum(ItemVendas.custo_unitario * ItemVendas.quantidade).label('custo'),
            func.min(Vendas.created_at).label('primeira'),
        )
        .join(Vendas, Vendas.id == ItemVendas.venda_id)
        .filter(*_filtros_vendas(usuario, intervalo), CONCLUIDA)
        .group_by(ItemVendas.produto_id)
        .subquery()
    )

    linhas = (
        db.query(
            Produtos.nome, Produtos.codigo_produto, Produtos.ativo, Produtos.quantidade, Produtos.estoque_min,
            Produtos.preco_compra, Produtos.preco_venda,
            func.coalesce(vendido.c.qtd, 0), func.coalesce(vendido.c.fat, 0),
            func.coalesce(vendido.c.custo, 0), vendido.c.primeira,
        )
        .outerjoin(vendido, vendido.c.produto_id == Produtos.id)
        .filter(Produtos.empresa_id == usuario.empresa_id,
                or_(Produtos.ativo.is_(True), vendido.c.qtd.isnot(None)))
        .all()
    )

    df = pd.DataFrame(linhas, columns=COLUNAS_PRODUTOS)
    for col in ('preco_compra', 'preco_venda', 'faturamento', 'custo'):
        df[col] = df[col].astype(float)
    for col in ('estoque', 'estoque_min', 'vendido'):
        df[col] = df[col].astype(int)
    df['ativo'] = df['ativo'].astype(bool)

    # Dias do período, para a média diária: do início do filtro (ou da 1ª venda) até o fim (ou agora).
    agora = datetime.now(timezone.utc)
    inicio = intervalo.inicio if intervalo and intervalo.inicio else None
    if inicio is None and df['primeira_venda'].notna().any():
        inicio = pd.Timestamp(df['primeira_venda'].min()).to_pydatetime()
    fim = intervalo.fim if intervalo and intervalo.fim else agora
    dias = max((fim - inicio).total_seconds() / 86400, 1.0) if inicio else None

    df['margem'] = (df['faturamento'] - df['custo']).round(2)
    df['margem_pct'] = (df['margem'] / df['faturamento'] * 100).where(df['faturamento'] > 0).round(2)
    df['giro'] = (df['vendido'] / df['estoque']).where(df['estoque'] > 0).round(2)
    df['media_diaria'] = (df['vendido'] / dias).round(2) if dias else 0.0
    df['dias_estoque'] = (df['estoque'] / df['media_diaria']).where(df['media_diaria'] > 0).round(1)
    df['valor_parado'] = (df['estoque'] * df['preco_compra']).round(2)
    df['faturamento'] = df['faturamento'].round(2)
    df['custo'] = df['custo'].round(2)

    ativos = df[df['ativo']]
    com_venda = df[df['vendido'] > 0]
    faturamento, custo = float(df['faturamento'].sum()), float(df['custo'].sum())

    resumo = {
        'total_produtos': len(ativos),
        'abaixo_estoque_min': int((ativos['estoque'] <= ativos['estoque_min']).sum()),
        'sem_estoque': int((ativos['estoque'] == 0).sum()),
        'valor_estoque_custo': round(float((ativos['estoque'] * ativos['preco_compra']).sum()), 2),
        'valor_estoque_venda': round(float((ativos['estoque'] * ativos['preco_venda']).sum()), 2),
        'unidades_vendidas': int(df['vendido'].sum()),
        'faturamento_bruto': round(faturamento, 2),  # antes do desconto da venda
        'custo_vendido': round(custo, 2),
        'margem': round(faturamento - custo, 2),
        'margem_pct': round((faturamento - custo) / faturamento * 100, 2) if faturamento else None,
        'produtos_sem_venda': int((ativos['vendido'] == 0).sum()),
        'dias_periodo': round(dias, 1) if dias else None,
    }

    reposicao = (
        ativos[ativos['estoque'] <= ativos['estoque_min']]
        .sort_values(['dias_estoque', 'estoque'], na_position='last')
        [['produto', 'codigo', 'estoque', 'estoque_min', 'media_diaria', 'dias_estoque']]
    )

    secoes = {
        'mais_vendidos': _ranking(com_venda[['produto', 'vendido', 'faturamento']], 'vendido', True, TOP_N_PRODUTOS),
        'maior_margem': _ranking(com_venda[['produto', 'margem', 'margem_pct']], 'margem', True, TOP_N_PRODUTOS),
        'menor_margem': _ranking(com_venda[['produto', 'margem', 'margem_pct']], 'margem', False, TOP_N_PRODUTOS),
        'sem_venda': _ranking(ativos[ativos['vendido'] == 0][['produto', 'estoque', 'valor_parado']],
                              'valor_parado', True, TOP_N_PRODUTOS),
        'reposicao': _registros(reposicao),
    }

    return resumo, secoes, df.drop(columns=['primeira_venda'])

def relatorio_produtos(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData] = None) -> dict:
    """JSON enxuto: resumo + rankings (top 10) + lista de reposição. A tabela completa só vai no Excel."""
    resumo, secoes, _ = _dados_relatorio_produtos(db, usuario, intervalo)
    return {'resumo': resumo, **secoes}

def exportar_relatorio_produtos(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData] = None) -> bytes:
    resumo, secoes, tabela = _dados_relatorio_produtos(db, usuario, intervalo)
    _registrar_exportacao(db, usuario, 'produtos', intervalo)
    return _excel({
        'Resumo': [resumo],
        'Produtos': tabela,
        'Reposição': secoes['reposicao'],
        'Sem Venda': secoes['sem_venda'],
        'Mais Vendidos': secoes['mais_vendidos'],
        'Maior Margem': secoes['maior_margem'],
        'Menor Margem': secoes['menor_margem'],
    })
