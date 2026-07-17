from decimal import Decimal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "local"
    database_url: str = "sqlite:///./queryshield.db"
    JWT_SECRET_KEY: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    BIGQUERY_DATASET_ID: str = "queryshield_demo"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_BYTES_BILLED: int = 100000000
    QUERY_RESULT_ROW_LIMIT: int = 100
    QUERY_TIMEOUT_SECONDS: int = 30
    BIGQUERY_ON_DEMAND_PRICE_PER_TIB: Decimal = Decimal("6.25")
    BIGQUERY_CURRENCY: str = "USD"
    STORAGE_BACKEND: str = "local"
    GCS_UPLOAD_BUCKET: str = ""
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    CSV_PREVIEW_ROWS: int = 10
    AI_SUMMARY_ENABLED: bool = True
    SUMMARY_MAX_ROWS: int = 25
    SUMMARY_MAX_CHARS: int = 6000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def frontend_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.FRONTEND_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def use_gcs_uploads(self) -> bool:
        return self.STORAGE_BACKEND.lower() == "gcs"

    @field_validator("MAX_BYTES_BILLED", "QUERY_RESULT_ROW_LIMIT", "QUERY_TIMEOUT_SECONDS", "SUMMARY_MAX_ROWS", "SUMMARY_MAX_CHARS")
    @classmethod
    def positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Configured query limits must be greater than 0")
        return value


settings = Settings()
