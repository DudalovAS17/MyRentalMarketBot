from __future__ import annotations

import logging
from functools import lru_cache
from typing import Final
from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# TELEGRAM_TOKEN = token_value("TELEGRAM_TOKEN")
# DATABASE_URL = database_url("DATABASE_URL")
# ADMIN_IDS = parse_admin_ids("ADMIN_IDS")

class Settings(BaseSettings):
    """Типизированная оболочка, чтобы удобно прокидывать конфиг в DI/инициализацию.

    Единый объект настроек приложения. Читается из ENV/.env, валидируется при старте.
    """

    model_config = SettingsConfigDict(
        env_file=".env", # BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # не падаем от лишних env-переменных
        case_sensitive=False,
        enable_decoding=False,  # ✅ костыль: отключаем JSON-decode для complex типов, для admin_ids
    )

    # --- Telegram ---
    telegram_token: SecretStr = Field(alias="TELEGRAM_TOKEN")

    @property
    def token_value(self) -> str:
        return self.telegram_token.get_secret_value()

    # --- Admins ---
    admin_ids: set[int] = Field(default_factory=set, alias="ADMIN_IDS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, admin_ids)-> set[int]:
        # None / "" / пустые контейнеры -> пустое множество
        if admin_ids in (None, "", [], (), set()):
            return set() # Это безопасно: приложение стартует, просто админка выключена.

        # Если кто-то передал список/кортеж/сет вручную
        if isinstance(admin_ids, (list, tuple, set)):
            return {int(x) for x in admin_ids if x is not None and str(x).strip()}
        # strip() - отбрасываем пустые/пробельные значения ("", " ") (убирает и табы/переводы строк)
        # Пример: [1, " 2 ", None, ""] → {1, 2}

        # Если внутри будет "foo" → int("foo") бросит ValueError → приложение упадёт на старте.
        # Это intentional: кривой конфиг лучше обнаружить сразу.

        # ENV почти всегда строка: "1, 2,3"
        s = str(admin_ids).strip()
        if not s:
            return set()

        return {int(x.strip()) for x in s.split(",") if x.strip()}
        # split(",") - разбивает строку по запятым ("123,456,789" → split → ["123", "456", "789"])
        # Если " 1, 2,3 ":
            # str(admin_ids).strip() → "1, 2,3"
            # split(",") → ["1", " 2", "3"]
            # x.strip() → "1", "2", "3"
            # int(...) → 1, 2, 3
            # set → {1,2,3}

    # --- PostgreSQL ---
    #database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")

    db_user: str = Field(default="postgres", alias="POSTGRES_USER")
    db_pass: SecretStr = Field(alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="aiogram-rentals-bot", alias="POSTGRES_DB")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_host: str = Field(default="postgres", alias="DB_HOST")

    @field_validator("db_port", mode="before")
    @classmethod
    def parse_db_port(cls, v):
        if v in (None, ""):
            return 5432
        return int(v)

    @field_validator("db_pass")
    @classmethod
    def validate_db_pass(cls, v: SecretStr):
        if not v.get_secret_value().strip():
            raise ValueError("POSTGRES_PASSWORD is empty")
        return v

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.db_user}:{self.db_pass.get_secret_value()}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # --- Redis ---
    #redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Значения вычисляются один раз при старте (при импорте), middleware/handlers не читают ENV каждый раз"""
    s = Settings()

    if not s.admin_ids: # Мягкое предупреждение, чтобы не удивляться “почему не работает админка”
        logger.warning("ADMIN_IDS is empty — admin access disabled")
    return s

settings: Final[Settings] = get_settings()


#-------------------- create_item_helpers ---------
"""
    def _env_required(name: str) -> str:
        value = os.getenv(name)
        if not value or not value.strip():
            raise RuntimeError(f"{name} is not set. Add it to your environment or to the .env file.")
        return value.strip()

    def _env_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            return default
        try:
            return int(raw.strip())
        except ValueError as e:
            raise RuntimeError(f"{name} must be an integer, got: {raw!r}") from e

"""