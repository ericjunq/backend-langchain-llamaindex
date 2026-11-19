from pydantic_settings import SettingsConfigDict, BaseSettings
from pathlib import Path
from typing import Literal

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expires_minutes: int = 15
    refresh_token_expires_days: int = 7
    algorithm: str = 'HS256'
    # Origens liberadas no CORS (frontend Angular). No .env: CORS_ORIGINS='["http://localhost:4200"]'
    cors_origins: list[str] = ['http://localhost:4200']
    # Fuso usado para definir o "dia" de uma venda (previsões e séries diárias).
    fuso_horario: str = 'America/Sao_Paulo'
    # Assistente (chat): modelo local via Ollama. Trocar de modelo = mudar OLLAMA_MODELO.
    ollama_url: str = 'http://localhost:11434'
    ollama_modelo: str = 'qwen3:8b'
    chat_max_passos: int = 5        # chamadas de ferramenta por mensagem (limita tempo e loops)
    chat_timeout_segundos: int = 120
    # Aplica as migrações pendentes ao subir a API (False = rodar à mão: python -m migracoes)
    migracoes_automaticas: bool = True
    # Retenção: de quanto em quanto tempo apagar tokens, convites e ações do chat vencidos
    limpeza_intervalo_horas: float = 24
    # Limite de login: falhas por (IP + email) dentro da janela → 429
    login_max_falhas: int = 5
    login_janela_minutos: int = 15
    # Emails de aviso: console (dev, só loga mascarado) | smtp | memoria (testes)
    email_backend: Literal['console', 'smtp', 'memoria'] = 'console'
    email_remetente: str = 'nao-responda@localhost'
    smtp_host: str = ''
    smtp_porta: int = 587
    smtp_usuario: str = ''
    smtp_senha: str = ''

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding="utf-8"
        )

settings = Settings()
