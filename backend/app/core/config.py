from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    APP_NAME: str = "Exalink Campo API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://exalink:exalink_pass@localhost:5432/exalink_campo"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://exalink:exalink_pass@localhost:5432/exalink_campo"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MQTT
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""

    # JWT
    SECRET_KEY: str = "CHANGE_ME_SUPER_SECRET_KEY_32CHARS_MIN"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # URL pública (dominio o IP) — usada en CORS y para construir links absolutos
    PUBLIC_URL: str = "https://campo.exalink.com.ar"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "https://campo.exalink.com.ar",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Notifications
    EVOLUTION_API_URL: str = ""
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@exalink.com"

    # LoRaWAN
    LORA_DB_PATH: str = "DB/lora.db"


settings = Settings()
