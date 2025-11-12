from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "llm_travel_backend"
    DATABASE_URL: str = "sqlite:///./travel.db"

    # Coza agent endpoint (or other LLM orchestration)
    COZA_AGENT_URL: str = ""
    # historical name in .env: COZA_AGENT_KEY
    COZA_AGENT_KEY: str = ""
    COZA_API_KEY: str = ""

    # Coze SDK (cozepy) integration
    COZE_API_TOKEN: str = ""
    # optional base url; e.g. COZE_CN_BASE_URL or custom
    COZE_API_BASE: str = ""
    # workflow id to run (string) - when set, provider will use the Coze SDK
    COZE_WORKFLOW_ID: str = ""
    # Timeout (seconds) to wait for Coze workflow HTTP runs. Set high because
    # workflows may be long-running. Default 300s (5 minutes).
    COZE_WORKFLOW_TIMEOUT: int = 60

    # 高德地图 (Amap) API
    AMAP_KEY: str = ""
    # NOTE: Server-side speech recognition provider (previously iFlyTek/XUNFEI)
    # has been removed from the codebase. Use the browser Web Speech API
    # (client-side) or configure an alternative provider if you require
    # server-side audio transcription. Any remaining environment keys
    # referencing XUNFEI in .env/.env.example are deprecated and ignored.

    # Supabase (optional) - when set, backend will use Supabase REST for cloud sync
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    JWT_SECRET: str = "CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()

# Backwards compatibility: if COZA_AGENT_KEY is supplied in env (older .env),
# map it to COZA_API_KEY to keep existing code working.
if settings.COZA_AGENT_KEY and not settings.COZA_API_KEY:
    settings.COZA_API_KEY = settings.COZA_AGENT_KEY
