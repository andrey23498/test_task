from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://payments:payments@localhost:5432/payments"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    api_key: SecretStr = SecretStr("local-development-key")
    debug: bool = False
    webhook_timeout: float = Field(default=10, gt=0)
    broker_publish_timeout: float = Field(default=10, gt=0)
    outbox_poll_interval: float = Field(default=1, gt=0)
    outbox_batch_size: int = Field(default=100, ge=1, le=1000)


settings = Settings()
