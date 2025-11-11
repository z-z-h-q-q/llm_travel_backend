from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "llm_travel_backend"
    DATABASE_URL: str = "sqlite:///./travel.db"

    # Coza agent endpoint (or other LLM orchestration)
    COZA_AGENT_URL: str = ""
    COZA_API_KEY: str = ""

    # 高德地图 (Amap) API
    AMAP_KEY: str = ""

    # 科大讯飞 (iFlyTek) 语音识别
    XUNFEI_APPID: str = ""
    XUNFEI_API_KEY: str = ""
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
