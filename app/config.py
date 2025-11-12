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

    # 科大讯飞 (iFlyTek) 语音识别
    XUNFEI_APPID: str = ""
    XUNFEI_API_KEY: str = ""
    # 讯飞 API Secret (用于签名)，控制台创建应用后可获取
    XUNFEI_API_SECRET: str = ""
    # 可选：讯飞的 REST 识别和大模型端点（在控制台或代理上配置）
    XUNFEI_SPEECH_RECOGNITION_URL: str = ""
    XUNFEI_LLM_URL: str = ""

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
