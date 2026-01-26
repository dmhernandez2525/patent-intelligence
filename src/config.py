import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Patent Intelligence"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/patent_intelligence"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # USPTO API
    uspto_api_key: str = ""
    uspto_base_url: str = "https://search.patentsview.org/api/v1"

    # EPO OPS API
    epo_consumer_key: str = ""
    epo_consumer_secret: str = ""
    epo_base_url: str = "https://ops.epo.org/3.2"

    # AI/LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    embedding_model: str = "AI-Growth-Lab/PatentSBERTa"
    embedding_dimension: int = 768

    # Auth - SECRET_KEY must be set in environment for production
    # Using a sentinel value that will fail fast if not properly configured
    secret_key: str = ""
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    @property
    def validated_secret_key(self) -> str:
        """Return secret_key, raising error if not configured in production."""
        if not self.secret_key:
            if not self.debug:
                raise ValueError(
                    "SECRET_KEY environment variable must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            # In debug mode, generate a temporary key (will invalidate on restart)
            import warnings
            warnings.warn(
                "Using auto-generated SECRET_KEY in debug mode. "
                "Set SECRET_KEY env var for persistent sessions.",
                RuntimeWarning
            )
            return secrets.token_urlsafe(32)
        return self.secret_key

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate Limiting
    rate_limit_per_minute: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
