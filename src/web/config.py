"""Configuration for Alexandria Web UI."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """Web UI settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="ALEXANDRIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars from librarian config
    )

    # Database
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "alexandria"
    db_user: str = "alexandria"
    db_password: str = "alexandria"

    # Library paths
    library_root: Path = Field(default=Path("library"))

    # Web server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Security
    secret_key: str = "change-me-in-production"
    session_expire_minutes: int = 60 * 24 * 7  # 1 week

    # Auth mode: local, forward_auth, or both
    auth_mode: str = "local"
    forward_auth_user_header: str = "X-Forwarded-User"
    forward_auth_email_header: str = "X-Forwarded-Email"
    forward_auth_groups_header: str = "X-Forwarded-Groups"
    forward_auth_admin_group: str = "admins"

    # Features
    enable_registration: bool = False
    guest_access: bool = False

    # Auto-admin creation (for first-time setup)
    admin_username: str | None = None
    admin_password: str | None = None
    admin_email: str | None = None

    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = WebSettings()
