"""Modelo de linguagem roteirizado: substitui o Ollama nos testes (rápido e determinístico)."""
import itertools
import json
from langchain_core.messages import AIMessage, ToolMessage

_ids = itertools.count(1)


def chamar(_ferramenta: str, /, **args) -> AIMessage:
    """Resposta do modelo pedindo uma ferramenta."""
    return AIMessage(content='', tool_calls=[{'name': _ferramenta, 'args': args, 'id': f'chamada{next(_ids)}'}])


class ModeloRoteirizado:
    """Funciona como a fábrica (recebe as ferramentas) e como o modelo (.invoke)."""

    def __init__(self, *passos):
        self.passos = list(passos)
        self.chamadas = []      # mensagens recebidas em cada invoke
        self.ferramentas = []

    def __call__(self, ferramentas):
        self.ferramentas = ferramentas
        return self

    def invoke(self, mensagens):
        self.chamadas.append(list(mensagens))
        if not self.passos:
            return AIMessage('fim')
        passo = self.passos.pop(0)
        if isinstance(passo, Exception):
            raise passo
        return passo

    def saidas_ferramentas(self) -> list:
        """Conteúdo (JSON decodificado) de todas as respostas de ferramentas da última conversa."""
        return [json.loads(m.content) for m in self.chamadas[-1] if isinstance(m, ToolMessage)]
