from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/bankruptcy_ai"
    redis_url: str = "redis://redis:6379/2"
    crm_internal_url: str = "http://backend:8000"
    ai_studio_url: str = "http://ai-core:8001"
    ai_studio_webhook_secret: str = ""

    # Channels (optional at start)
    green_api_token: str = ""
    vk_api_token: str = ""
    meta_verify_token: str = ""
    meta_access_token: str = ""
    avito_client_id: str = ""
    avito_client_secret: str = ""
    ok_api_token: str = ""
    max_bot_token: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
