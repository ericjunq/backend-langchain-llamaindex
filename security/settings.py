from pydantic_settings import SettingsConfigDict, BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    database_url: str 
    secret_key: str 
    access_token_expires_minutes: int 
    refresh_token_expires_days: int 
    algorithm: str 
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding="utf-8"
        )

settings = Settings()
