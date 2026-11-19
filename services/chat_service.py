"""Assistente via chat: modelo local (Ollama) + laço de ferramentas.

O laço é nosso (não um agente pronto) para controlar: nº máximo de passos, erros das
ferramentas, tempo e o que volta para o usuário. O modelo é injetado (fábrica), então os
testes usam um modelo roteirizado sem precisar do Ollama.
"""
import re
from typing import Callable

import httpx
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from sqlalchemy.orm import Session

from models.empresa_model import Empresa
from models.usuario_model import Usuarios
from schemas.chat_schema import ChatRequest
from security.permissoes import exigir_empresa
from security.settings import settings
from services.chat_ferramentas import criar_ferramentas_escrita, criar_ferramentas_leitura, executar_ferramenta
from services.previsao_service import hoje_local

# fábrica(ferramentas) -> objeto com .invoke(mensagens) -> AIMessage
FabricaModelo = Callable[[list], object]

PROMPT_SISTEMA = """Você é o assistente do sistema de gestão da empresa "{empresa}".
Quem está falando: {nome} (cargo: {cargo}). Hoje é {hoje}.

Regras:
- Responda em português do Brasil, de forma curta e direta.
- Use as ferramentas para obter dados. NUNCA invente números, produtos, clientes ou vendas.
- Valores em dinheiro de reposição ou previsão são ESTIMATIVAS: diga "estimado".
- Sobre reposição, comece pelo nível de necessidade: quantos produtos precisam de compra e quais.
- Mencione a confiança da previsão quando ela for baixa.
- Se uma ferramenta devolver "erro" (por exemplo, falta de permissão), explique isso ao usuário.
- Nunca peça nem mostre CPF, email ou telefone.
- Para registrar venda, repor estoque ou cancelar venda, use registrar_venda, repor_estoque ou cancelar_venda:
  elas só PREPARAM a ação
  e devolvem uma "situacao" que você deve repassar ao usuário. Nunca diga que a ação já foi feita.
- Se faltar informação para uma venda (produto, quantidade ou forma de pagamento), pergunte antes.
- Cancelar venda exige o MOTIVO dito pelo usuário. Se ele não disse, pergunte o motivo antes de cancelar.
"""

MENSAGEM_LIMITE_PASSOS = ('Não consegui concluir essa resposta com segurança. '
                          'Tente reformular a pergunta de forma mais específica.')

_PENSAMENTO = re.compile(r'<think>.*?</think>', re.DOTALL)


def get_fabrica_modelo() -> FabricaModelo:
    """Dependência do FastAPI (substituída nos testes)."""
    from langchain_ollama import ChatOllama

    def criar(ferramentas: list):
        return ChatOllama(
            model=settings.ollama_modelo,
            base_url=settings.ollama_url,
            temperature=0,           # respostas estáveis e factuais
            reasoning=False,         # sem "modo pensamento" do qwen3: bem mais rápido
            keep_alive='30m',        # mantém o modelo carregado entre mensagens
            client_kwargs={'timeout': settings.chat_timeout_segundos},
        ).bind_tools(ferramentas)

    return criar


def _limpar(texto) -> str:
    texto = texto if isinstance(texto, str) else str(texto or '')
    return _PENSAMENTO.sub('', texto).strip()


def conversar(db: Session, usuario: Usuarios, dados: ChatRequest, fabrica: FabricaModelo) -> dict:
    exigir_empresa(usuario)

    pendentes: list = []  # ações de escrita preparadas nesta mensagem (aguardam confirmação)
    ferramentas = criar_ferramentas_leitura(db, usuario) + criar_ferramentas_escrita(db, usuario, pendentes)
    por_nome = {f.name: f for f in ferramentas}
    modelo = fabrica(ferramentas)

    empresa = db.get(Empresa, usuario.empresa_id)
    mensagens = [SystemMessage(PROMPT_SISTEMA.format(
        empresa=empresa.nome, nome=usuario.nome, cargo=usuario.cargo.value if usuario.cargo else '-',
        hoje=hoje_local().strftime('%d/%m/%Y')))]
    for m in dados.historico:
        mensagens.append(HumanMessage(m.conteudo) if m.papel == 'usuario' else AIMessage(m.conteudo))
    mensagens.append(HumanMessage(dados.mensagem))

    usadas: list[str] = []
    resposta = MENSAGEM_LIMITE_PASSOS
    for _ in range(settings.chat_max_passos + 1):
        try:
            ai = modelo.invoke(mensagens)
        except (httpx.HTTPError, ConnectionError, TimeoutError) as e:
            raise HTTPException(status_code=503, detail='Assistente indisponível no momento') from e

        mensagens.append(ai)
        if not ai.tool_calls:
            resposta = _limpar(ai.content) or 'Não tenho uma resposta para isso.'
            break
        if len(usadas) >= settings.chat_max_passos:
            break  # passou do limite de passos: resposta padrão

        for chamada in ai.tool_calls:
            usadas.append(chamada['name'])
            ferramenta = por_nome.get(chamada['name'])
            saida = (executar_ferramenta(ferramenta, chamada.get('args') or {}) if ferramenta
                     else '{"erro":"ferramenta inexistente"}')
            mensagens.append(ToolMessage(content=saida, tool_call_id=chamada['id']))

    return {'resposta': resposta, 'ferramentas_usadas': usadas, 'acoes_pendentes': pendentes}
