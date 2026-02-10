from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot
    bot_token: str

    # Pyrogram (userbot)
    api_id: int
    api_hash: str
    phone_number: str

    # OpenRouter
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "tngtech/deepseek-r1t2-chimera:free"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery Beat Schedule
    digest_hour: int = 9
    digest_minute: int = 0


settings = Settings()
