import httpx
from ..config import settings
from typing import Any


async def extract_basicinfo_with_iflytek(text: str) -> dict:
    """Call iFlyTek large model to extract BasicInfo from free-form text.
    Expects settings.XUNFEI_LLM_URL to be configured to accept a JSON payload like:
      {"input": "<text>", "task": "extract_basic_info"}
    and return JSON {"basic_info": {...}}.

    This is intentionally generic - adapt to the real iFlyTek API shape or proxy in front.
    """
    if not settings.XUNFEI_LLM_URL:
        raise RuntimeError("XUNFEI_LLM_URL not configured")

    payload = {"input": text, "task": "extract_basic_info"}
    headers = {"Content-Type": "application/json"}
    # If XUNFEI_API_KEY is set, include it as Authorization Bearer (or adapt as needed)
    if settings.XUNFEI_API_KEY:
        headers["Authorization"] = f"Bearer {settings.XUNFEI_API_KEY}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.XUNFEI_LLM_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Expecting data.{basic_info,text} or similar
    if isinstance(data, dict) and data.get("basic_info"):
        return data["basic_info"]

    # try common alternatives
    if isinstance(data, dict) and data.get("result") and isinstance(data["result"], dict):
        return data["result"].get("basic_info", {})

    # fallback: return empty dict
    return {}
