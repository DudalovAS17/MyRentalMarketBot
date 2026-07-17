from __future__ import annotations

import logging
from functools import lru_cache
from typing import Final
from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

"""
    TELEGRAM_TOKEN = token_value("TELEGRAM_TOKEN")
    DATABASE_URL = database_url("DATABASE_URL")
    ADMIN_IDS = parse_admin_ids("ADMIN_IDS")
"""

class Settings(BaseSettings):
    """Единый typed config приложения."""

    ENV_FILE: str = ".env"  # ENV_FILE: Final[Path] = BASE_DIR / ".env"
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    # ───────── Runtime  ─────────
    debug: bool = Field(default=True, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    drop_pending_updates: bool = Field(default=False, alias="DROP_PENDING_UPDATES")
    storage_path: str = Field(default="storage", validation_alias="STORAGE_PATH")

    @property
    def log_level_value(self) -> int:
        """Вернуть numeric logging level."""
        return logging.getLevelName(self.log_level)

    # ───────── Telegram ─────────
    telegram_token: SecretStr = Field(alias="TELEGRAM_TOKEN")

    @property
    def token_value(self) -> str:
        """Вернуть Telegram token как обычную строку."""
        return self.telegram_token.get_secret_value()

    @field_validator("telegram_token")
    @classmethod
    def validate_telegram_token(cls, value: SecretStr) -> SecretStr:
        """Проверить, что TELEGRAM_TOKEN не пустой."""
        if not value.get_secret_value().strip():
            raise ValueError("TELEGRAM_TOKEN is empty")
        return value

    # ───────── Admins ─────────
    admin_ids: set[int] = Field(default_factory=set, alias="ADMIN_IDS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, admin_ids: object)-> set[int]:
        """Распарсить ADMIN_IDS."""
        if admin_ids in (None, "", [], (), set()):
            return set()
        if isinstance(admin_ids, (list, tuple, set)):
            return {int(x) for x in admin_ids if x is not None and str(x).strip()}

        s = str(admin_ids).strip()
        if not s:
            return set()

        try:
            return {int(x.strip()) for x in s.split(",") if x.strip()}
        except ValueError as exc:
            raise ValueError("ADMIN_IDS must be like: ADMIN_IDS=123456789,987654321") from exc

    def log_startup_warnings(self) -> None:
        """Вывести мягкие startup-предупреждения после настройки logging."""
        if not self.admin_ids:
            logger.warning("ADMIN_IDS is empty — admin access disabled")

    # ───────── PosTgreSQL ─────────
    #database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    db_user: str = Field(default="postgres", alias="POSTGRES_USER")
    db_pass: SecretStr = Field(alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="rental_market_bot", alias="POSTGRES_DB")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_host: str = Field(default="postgres", alias="DB_HOST")

    @field_validator("db_port", mode="before")
    @classmethod
    def parse_db_port(cls, v):
        """Распарсить и проверить DB_PORT."""
        if v in (None, ""):
            return 5432
        return int(v)

    @field_validator("db_pass")
    @classmethod
    def validate_db_pass(cls, v: SecretStr):
        """Проверить, что POSTGRES_PASSWORD не пустой."""
        if not v.get_secret_value().strip():
            raise ValueError("POSTGRES_PASSWORD is empty")
        return v

    @computed_field
    @property
    def database_url(self) -> str:
        """Собрать SQLAlchemy async database URL."""
        return (
            "postgresql+asyncpg://"
            f"{self.db_user}:{self.db_pass.get_secret_value()}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @field_validator("db_user", "db_name", "db_host")
    @classmethod
    def validate_non_empty_string(cls, value: str) -> str:
        """Проверить строковые DB-настройки."""
        value = value.strip()

        if not value:
            raise ValueError("Database setting cannot be empty")

        return value

    # ───────── Redis ─────────
    #redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Вернуть singleton Settings."""

    # noinspection PyArgumentList
    return Settings()


settings: Final[Settings] = get_settings()