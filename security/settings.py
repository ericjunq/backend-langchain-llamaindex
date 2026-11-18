from pydantic_settings import SettingsConfigDict, BaseSettings
from pathlib import Path

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

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding="utf-8"
        )

settings = Settings()
