"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bankruptcy AI Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bankruptcy_ai"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # AI Core
    AI_CORE_URL: str = "http://localhost:8001"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""  # fallback

    # File storage (S3-compatible, legacy local)
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minio"
    S3_SECRET_KEY: str = "minio123"
    S3_BUCKET: str = "bankruptcy-documents"

    # Yandex Object Storage (knowledge base)
    YC_ACCESS_KEY: str = ""
    YC_SECRET_KEY: str = ""
    YC_ENDPOINT_URL: str = "https://storage.yandexcloud.net"
    YC_BUCKET_NAME: str = "bankruptcy-ai-knowledge"
    YC_PRESIGNED_URL_TTL: int = 3600

    # Internal service auth
    INTERNAL_SECRET: str = "change-me-internal-secret"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Next.js dev
        "http://localhost:8000",
    ]

    # External services
    TELEGRAM_BOT_TOKEN: str = ""
    WHATSAPP_API_TOKEN: str = ""

    # Lead collector (external public registries)
    LEAD_COLLECTOR_MOCK_MODE: bool = True
    LEAD_COLLECTOR_TIMEOUT_SECONDS: int = 20
    LEAD_COLLECTOR_MAX_RETRIES: int = 3
    LEAD_COLLECTOR_PAGE_SIZE: int = 100
    FSSP_API_URL: str = ""
    FSSP_API_KEY: str = ""
    KAD_API_URL: str = ""
    KAD_API_KEY: str = ""
    EFRSB_API_URL: str = ""
    EFRSB_API_KEY: str = ""
    FNS_API_URL: str = ""
    ROSREESTR_API_URL: str = ""
    ROSREESTR_API_KEY: str = ""

    # Outreach worker
    LEAD_OUTREACH_DRY_RUN: bool = True
    LEAD_OUTREACH_BATCH_SIZE: int = 100
    LEAD_OUTREACH_SMS_API_URL: str = ""
    LEAD_OUTREACH_SMS_API_KEY: str = ""
    LEAD_OUTREACH_EMAIL_API_URL: str = ""
    LEAD_OUTREACH_EMAIL_API_KEY: str = ""
    LEAD_OUTREACH_FROM_EMAIL: str = "no-reply@bankrotstvo.ai"
    LEAD_OUTREACH_TELEGRAM_BOT_TOKEN: str = ""

    # SMS Gateway (for client auth + e-signatures)
    SMS_API_KEY: str = ""
    SMS_PROVIDER: str = "smsru"  # smsru | smsc | twillio
    SMS_SENDER: str = "Bankrot.AI"

    # Tochka Bank API
    TOCHKA_API_URL: str = "https://enter.tochka.com/api/v2"
    TOCHKA_API_TOKEN: str = ""
    TOCHKA_ACCOUNT_ID: str = ""
    TOCHKA_WEBHOOK_SECRET: str = ""

    # E-Signature
    ESIGN_CODE_EXPIRE_MINUTES: int = 10
    ESIGN_MAX_ATTEMPTS: int = 5

    # Company details (for documents and invoices)
    COMPANY_NAME: str = "ООО «Банкротство.AI»"
    COMPANY_INN: str = ""
    COMPANY_OGRN: str = ""
    COMPANY_ADDRESS: str = ""
    COMPANY_BANK_NAME: str = "АО «Точка»"
    COMPANY_BIK: str = ""
    COMPANY_ACCOUNT: str = ""
    COMPANY_CORR_ACCOUNT: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
