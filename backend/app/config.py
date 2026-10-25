from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://localhost:5432/urbansense"
    jwt_secret: str = ""
    device_encryption_key: str = ""
    us_admin_token: str = ""
    dashboard_email: str = ""
    dashboard_password: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_event_age_seconds: int = 900
    future_clock_skew_seconds: int = 300
    high_temperature_threshold_c: float = Field(default=40.0, ge=-50, le=100)
    high_temperature_consecutive_readings: int = Field(default=2, ge=1, le=100)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
