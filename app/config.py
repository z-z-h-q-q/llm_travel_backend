import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseSettings


# Load dotenv file if present. Priority:
# 1. Path specified by ENV_FILE environment variable
# 2. /run/secrets/.env (Docker secret or mounted file)
# 3. .env in the repository root
# We call load_dotenv with override=False so that any environment variables
# passed to the process (e.g., via `docker run -e`) keep precedence over file values.
dotenv_candidates = [
    os.getenv('ENV_FILE'),
    '/run/secrets/.env',
    str(Path(__file__).resolve().parents[1] / '.env'),
    '.env',
]

for candidate in dotenv_candidates:
    if candidate and Path(candidate).exists():
        load_dotenv(dotenv_path=candidate, override=False)
        break


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

    # 星火 / 其他 LLM API (可配置为星火 Lite 的 HTTP 接口)
    # Example: XINGHUO_API_URL=https://api.example.com/v1/models/xinghuo-lite/chat
    XINGHUO_API_URL: str = ""
    # Bearer token or API key for the LLM provider. The provider may expect a
    # specific header; this code will send it as Authorization: Bearer <key>.
    XINGHUO_API_KEY: str = ""
    # Default model to call on the Xinghuo API (e.g. generalv3.5)
    XINGHUO_MODEL: str = "generalv3.5"

    # Supabase (optional) - when set, backend will use Supabase REST for cloud sync
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    JWT_SECRET: str = "CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"


settings = Settings()

# Backwards compatibility: if COZA_AGENT_KEY is supplied in env (older .env),
# map it to COZA_API_KEY to keep existing code working.
if settings.COZA_AGENT_KEY and not settings.COZA_API_KEY:
    settings.COZA_API_KEY = settings.COZA_AGENT_KEY
