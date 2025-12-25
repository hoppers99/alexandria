"""Configuration management for The Librarian."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="ALEXANDRIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore deprecated env vars like SOURCE_LIBRARY
    )

    # Database
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "alexandria"
    db_user: str = "alexandria"
    db_password: str = "alexandria"

    # Library paths (destination for organised files)
    # The library_root should contain: Fiction/, Non-Fiction/, .returns/
    library_root: Path = Field(default=Path("library"))

    @property
    def returns_dir(self) -> Path:
        """Returns folder for incoming items."""
        return self.library_root / ".returns"

    @property
    def source_dir(self) -> Path:
        """Alias for returns_dir - where source files awaiting review are located."""
        return self.returns_dir

    @property
    def covers_dir(self) -> Path:
        """Directory for cover images."""
        return self.library_root / ".covers"

    # Calibre integration (optional, for metadata enrichment during migration)
    calibre_library: Path | None = Field(default=None)
    enable_calibre: bool = False

    # Naming
    author_format: str = "first_last"  # or "last_first"
    series_format: str = "{author} - {series} {number:02d} - {title}"
    standard_format: str = "{author} - {title}"

    # Classification
    auto_file: bool = True
    confidence_threshold: float = 0.8

    # API settings
    enable_oclc: bool = True
    enable_openlibrary: bool = True
    enable_google_books: bool = True
    enable_librarything: bool = True
    librarything_api_key: str | None = None  # Optional, for extended API access

    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


# Global settings instance
settings = Settings()
