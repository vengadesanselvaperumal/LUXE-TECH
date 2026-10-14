import secrets
from functools import lru_cache
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    GEMINI_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    DATABASE_URL: str = "sqlite:///./backend/luxe_tech.db"
    SECRET_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def ensure_secret_key(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else secrets.token_urlsafe(48)

    @field_validator("GEMINI_MODEL", mode="before")
    @classmethod
    def ensure_gemini_model(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else "gemini-3.1-flash-lite"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod")

    @property
    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if self.is_production:
            if not raw:
                raise ValueError("CORS_ORIGINS must be explicitly configured in production and cannot be empty.")
            origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
            if "*" in origins:
                raise ValueError("Wildcard '*' CORS origin is strictly forbidden in production.")
            for origin in origins:
                if not (origin.startswith("http://") or origin.startswith("https://")):
                    raise ValueError(f"Invalid CORS origin '{origin}': must include http:// or https:// scheme.")
            return origins

        # Safe local development fallback:
        if not raw:
            return [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def has_supabase(self) -> bool:
        return bool(self.SUPABASE_URL and (self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_ANON_KEY))

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def has_youtube(self) -> bool:
        return bool(self.YOUTUBE_API_KEY and self.YOUTUBE_API_KEY.strip())


@lru_cache()
def get_settings() -> Settings:
    return Settings()
