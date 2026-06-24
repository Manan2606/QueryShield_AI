from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    gcp_project_id: str = ""
    bigquery_dataset_id: str = "queryshield_demo"
    gemini_api_key: str = ""
    max_bytes_billed: int = 100000000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
