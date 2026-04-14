import secrets

from pydantic import model_validator
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

    @model_validator(mode="after")
    def check_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if self.auth_token_owner in ("change-me-owner", ""):
                raise ValueError("AUTH_TOKEN_OWNER must be set to a secure value in production")
            if self.auth_token_admin in ("change-me-admin", ""):
                raise ValueError("AUTH_TOKEN_ADMIN must be set to a secure value in production")
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def token_to_role(self, token: str) -> str | None:
        """Map a bearer token to a role. Returns None if invalid."""
        if secrets.compare_digest(token, self.auth_token_owner):
            return "owner"
        if secrets.compare_digest(token, self.auth_token_admin):
            return "admin"
        return None


settings = Settings()
