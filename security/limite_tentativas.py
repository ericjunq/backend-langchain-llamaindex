"""Limite de tentativas de login (contra força bruta).

Conta FALHAS por chave (IP + email) numa janela deslizante. Ao passar do limite, responde 429
com Retry-After. Um login certo zera a contagem daquela chave.

Por que IP + email (e não só email): só pelo email, um atacante bloquearia a conta de qualquer
pessoa de propósito. Só pelo IP, ele testaria muitas contas a partir do mesmo IP sem limite por conta.

Limitação conhecida: fica em memória, por processo. Com vários workers/servidores, cada um conta
separado → em produção, trocar por Redis (mesma interface). Atrás de proxy, rodar o uvicorn com
--proxy-headers para o IP real chegar aqui.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from security.settings import settings


class LimiteTentativas:
    def __init__(self, maximo: int, janela_segundos: int):
        self.maximo = maximo
        self.janela = janela_segundos
        self._falhas: dict[str, deque] = defaultdict(deque)
        self._trava = threading.Lock()

    def _limpar_antigas(self, fila: deque, agora: float) -> None:
        while fila and agora - fila[0] > self.janela:
            fila.popleft()

    def verificar(self, chave: str) -> None:
        agora = time.monotonic()
        with self._trava:
            fila = self._falhas.get(chave)
            if not fila:
                return
            self._limpar_antigas(fila, agora)
            if len(fila) >= self.maximo:
                espera = int(self.janela - (agora - fila[0])) + 1
                raise HTTPException(status_code=429, detail='Muitas tentativas de login. Tente novamente mais tarde.',
                                    headers={'Retry-After': str(espera)})

    def registrar_falha(self, chave: str) -> None:
        agora = time.monotonic()
        with self._trava:
            fila = self._falhas[chave]
            self._limpar_antigas(fila, agora)
            fila.append(agora)
            if len(self._falhas) > 10_000:  # evita crescer sem fim: descarta chaves sem falha recente
                for k in [k for k, f in self._falhas.items() if not f or agora - f[-1] > self.janela]:
                    del self._falhas[k]

    def limpar(self, chave: str) -> None:
        with self._trava:
            self._falhas.pop(chave, None)

    def resetar(self) -> None:
        with self._trava:
            self._falhas.clear()


limite_login = LimiteTentativas(settings.login_max_falhas, settings.login_janela_minutos * 60)
