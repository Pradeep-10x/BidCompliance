from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "PRAMAAN"
    ENVIRONMENT: str = "development"

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "sih_project"
    POSTGRES_DB_TEST: str = "sih_project_test"

    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_ROOT: str = "storage"
    STORAGE_ENDPOINT: str | None = None
    STORAGE_ACCESS_KEY: str | None = None
    STORAGE_SECRET_KEY: str | None = None
    STORAGE_BUCKET: str = "documents"
    STORAGE_SECURE: bool = False
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    PROCESSING_JOB_MAX_ATTEMPTS: int = 3
    ML1_BASE_URL: str = "http://localhost:8001"
    ML1_CONNECT_TIMEOUT_SECONDS: float = 5.0
    ML1_READ_TIMEOUT_SECONDS: float = 30.0
    ML1_TOTAL_TIMEOUT_SECONDS: float = 35.0

    # Compatibility settings for the synchronous SIH demonstration path.
    STORAGE_ROOT: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 25
    ML_SERVICE_URL: str = "http://localhost:8001"
    ML_REQUEST_TIMEOUT_SECONDS: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def TEST_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_TEST}"
        )


settings = Settings()
