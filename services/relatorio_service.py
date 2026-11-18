from io import BytesIO
from typing import Optional
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from models.cliente_model import Clientes
from models.produto_model import Produtos
from models.vendas_model import Vendas, ItemVendas
from models.usuario_model import Usuarios
from security.permissoes import exigir_cargo
from utils.enums import CargosEnum, StatusVenda
from utils.data_filter import IntervaloData, filtros_intervalo

TOP_N = 5

def _ranking(df: pd.DataFrame, coluna: str, maiores: bool) -> list:
    if df.empty:
        return []
    escolhidos = df.nlargest(TOP_N, coluna) if maiores else df.nsmallest(TOP_N, coluna)
    return escolhidos.to_dict(orient='records')

def _dados_relatorio(db: Session, usuario: Usuarios, intervalo: Optional[IntervaloData]):
    """4 consultas no total: 1 de resumo + 1 agregada por entidade (produto, funcionário, cliente).
    Os rankings (top/bottom 5) saem do mesmo resultado em memória, em vez de 1 consulta por ranking."""
    exigir_cargo(usuario, CargosEnum.dono)

    filtros = [Vendas.empresa_id == usuario.empresa_id, *filtros_intervalo(Vendas.created_at, intervalo)]
    concluida = Vendas.status != StatusVenda.cancelada

    total, canceladas, clientes_distintos, faturamento = db.query(
        func.count(Vendas.id),
        func.count(Vendas.id).filter(Vendas.status == StatusVenda.cancelada),
        func.count(func.distinct(Vendas.cliente_id)).filter(concluida),
        func.coalesce(func.sum(Vendas.valor_final).filter(concluida), 0),
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
        db.query(
            Produtos.nome,
            func.sum(ItemVendas.quantidade),
            func.sum(ItemVendas.subtotal),
        )
        .join(ItemVendas, ItemVendas.produto_id == Produtos.id)
        .join(Vendas, Vendas.id == ItemVendas.venda_id)
        .filter(*filtros, concluida)
        .group_by(Produtos.id, Produtos.nome)
        .all(),
        columns=['produto', 'quantidade', 'valor_total'],
    )

    funcionarios = pd.DataFrame(
        db.query(Usuarios.nome, func.count(Vendas.id), func.sum(Vendas.valor_final))
        .join(Vendas, Vendas.usuario_id == Usuarios.id)
        .filter(*filtros, concluida)
        .group_by(Usuarios.id, Usuarios.nome)
        .all(),
        columns=['nome', 'quantidade', 'valor_total'],
    )

    clientes = pd.DataFrame(
        db.query(Clientes.nome, func.count(Vendas.id), func.sum(Vendas.valor_final))
        .join(Vendas, Vendas.cliente_id == Clientes.id)
        .filter(*filtros, concluida)
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
    resumo, rankings = _dados_relatorio(db, usuario, intervalo)
    return {'resumo': resumo, **rankings}

ABAS = {
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
    """Gera o Excel em memória: nada fica salvo no disco do servidor (LGPD: contém nomes de clientes)."""
    resumo, rankings = _dados_relatorio(db, usuario, intervalo)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame([resumo]).to_excel(writer, sheet_name='Resumo', index=False)
        for chave, aba in ABAS.items():
            pd.DataFrame(rankings[chave]).to_excel(writer, sheet_name=aba, index=False)

    return buffer.getvalue()
