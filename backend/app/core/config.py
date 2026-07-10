from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./queryshield.db"
    JWT_SECRET_KEY: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    GCP_PROJECT_ID: str = ""
    BIGQUERY_DATASET_ID: str = "queryshield_demo"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_BYTES_BILLED: int = 100000000
    BIGQUERY_ON_DEMAND_PRICE_PER_TIB: Decimal = Decimal("6.25")
    BIGQUERY_CURRENCY: str = "USD"
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    CSV_PREVIEW_ROWS: int = 10

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


settings = Settings()
