from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/billsnap"

    # Auth — static bearer tokens mapped to user roles
    auth_token_owner: str = "change-me-owner"
    auth_token_admin: str = "change-me-admin"

    # OCR
    anthropic_api_key: str = ""
    ocr_confidence_threshold: float = 0.70
    ocr_stuck_job_timeout: int = 300  # seconds

    # Storage
    storage_bucket: str = "billsnap-storage"
    storage_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-south-1"
    signed_url_ttl: int = 900  # 15 minutes

    # Worker
    ocr_worker_poll_interval: int = 3

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def token_to_role(self, token: str) -> str | None:
        """Map a bearer token to a role. Returns None if invalid."""
        if token == self.auth_token_owner:
            return "owner"
        if token == self.auth_token_admin:
            return "admin"
        return None


settings = Settings()
