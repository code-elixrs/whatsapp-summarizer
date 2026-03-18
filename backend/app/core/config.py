from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str = "lifelog"
    POSTGRES_PASSWORD: str = "lifelog_dev_password"
    POSTGRES_DB: str = "lifelog"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    REDIS_URL: str = "redis://redis:6379/0"

    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    UPLOAD_DIR: str = "/app/uploads"

    # Whisper transcription
    WHISPER_MODEL_DIR: str = "/models"
    WHISPER_DEFAULT_MODEL: str = "base"
    WHISPER_DEVICE: str = "auto"  # "auto", "cuda", "cpu"
    WHISPER_COMPUTE_TYPE: str = "auto"  # "auto", "int8", "float16", "float32"
    TRANSCRIPTION_CONCURRENCY: int = 1

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
