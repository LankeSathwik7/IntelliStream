"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App Config
    environment: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Groq LLM
    groq_api_key: str = ""

    # Voyage AI Embeddings (backup)
    voyage_api_key: str = ""

    # OpenAI Embeddings (primary - faster)
    openai_api_key: str = ""

    # Upstash Redis
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # Axiom Monitoring
    axiom_token: Optional[str] = None
    axiom_org_id: Optional[str] = None
    axiom_dataset: str = "intellistream-logs"

    # Web Search (Tavily - optional, 1000 free searches/month)
    tavily_api_key: Optional[str] = None

    # News API (optional, 100 requests/day free)
    newsapi_key: Optional[str] = None

    # OpenWeatherMap (optional, 1000 calls/day free)
    openweather_api_key: Optional[str] = None

    # Alpha Vantage (optional, 25 requests/day free)
    alphavantage_api_key: Optional[str] = None

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def is_configured(self) -> bool:
        """Check if all required services are configured."""
        return all(
            [
                self.supabase_url,
                self.supabase_service_role_key,
                self.groq_api_key,
                self.voyage_api_key,
            ]
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
