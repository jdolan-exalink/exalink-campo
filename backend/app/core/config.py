from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    APP_NAME: str = "Exalink Campo API"
    APP_VERSION: str = "0.2.1"
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

    # Pairing (gateways & devices LoRa)
    # TTL del código de pairing en minutos. Mientras el GW siga pending y haga
    # /gateway/sync, el server re-estampa este valor (auto-renew).
    PAIRING_TTL_MIN: int = 30
    # Si está activo, el server re-estampa el expiry cada vez que un GW pending
    # reporta por /gateway/sync. Si el usuario lo desactiva, el código expira
    # estrictamente al cabo de PAIRING_TTL_MIN desde que el GW lo generó.
    PAIRING_AUTO_RENEW: bool = True
    # Rate-limit de intentos de pairing por (target_id, ip). 0 desactiva.
    PAIRING_MAX_ATTEMPTS: int = 10
    # Ventana del rate-limit en segundos.
    PAIRING_RATE_WINDOW_S: int = 60

    # Comportamiento de /lora/ingest frente a devices no pareados.
    # LORA_REQUIRE_PAIRING=True: sólo se guardan en `packets` las lecturas de
    #   devices con is_paired=1. Las lecturas de devices desconocidos o no
    #   pareados se descartan (la fila del device se auto-registra igual para
    #   que aparezca en /devices/pending). Los packets con dev_addr que
    #   empieza con "gw:" (lecturas propias del gateway) se guardan siempre.
    # LORA_REQUIRE_PAIRING=False: comportamiento histórico — se guarda todo.
    LORA_REQUIRE_PAIRING: bool = True


settings = Settings()
