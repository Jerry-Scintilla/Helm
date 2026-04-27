from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Helm"
    app_env: str = "development"
    app_secret_key: str = "change-me"
    app_url: str = "http://localhost:8000"

    db_url: str = "postgresql+asyncpg://helm:helm@127.0.0.1:5432/helm"
    redis_url: str = "redis://127.0.0.1:6379/0"

    eve_client_id: str = ""
    eve_client_secret: str = ""
    eve_callback_url: str = "http://localhost:8000/auth/eve/callback"

    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_access_token_expire: int = 900
    jwt_refresh_token_expire: int = 2592000

    celery_broker_url: str = "redis://127.0.0.1:6379/1"
    celery_result_backend: str = "redis://127.0.0.1:6379/2"


settings = Settings()
