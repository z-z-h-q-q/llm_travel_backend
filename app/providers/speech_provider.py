import httpx
from ..config import settings
from typing import Any
from ..utils import basicinfo_from_text
from .iflytek_provider import extract_basicinfo_with_iflytek


async def recognize_iflytek(audio_bytes: bytes, fmt: str = "wav") -> str:
    """Attempt to transcribe audio using configured iFlyTek speech endpoint.
    If settings.XUNFEI_SPEECH_RECOGNITION_URL is set, POST multipart/form-data with 'audio'.
    Otherwise raise RuntimeError.
    """
    if not settings.XUNFEI_SPEECH_RECOGNITION_URL:
        raise RuntimeError("XUNFEI_SPEECH_RECOGNITION_URL not configured")

    headers = {}
    if settings.XUNFEI_API_KEY:
        headers["Authorization"] = f"Bearer {settings.XUNFEI_API_KEY}"

    files = {"audio": (f"recording.{fmt}", audio_bytes, f"audio/{fmt}")}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.XUNFEI_SPEECH_RECOGNITION_URL, files=files, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # try common response patterns
    if isinstance(data, dict):
        if data.get("text"):
            return data["text"]
        if data.get("data") and isinstance(data.get("data"), dict) and data.get("data").get("text"):
            return data["data"]["text"]

    # fallback: convert bytes to str (unlikely) or raise
    raise RuntimeError("iFlyTek response did not include transcription text")


async def transcribe_and_extract_basicinfo(audio_bytes: bytes, fmt: str = "wav") -> dict:
    """Transcribe audio and then extract BasicInfo using iFlyTek LLM if available.
    Returns dict with keys: text, basic_info
    """
    text = await recognize_iflytek(audio_bytes, fmt=fmt)

    # Try LLM extraction if configured
    basic_info = {}
    try:
        if settings.XUNFEI_LLM_URL:
            basic_info = await extract_basicinfo_with_iflytek(text)
        else:
            basic_info = basicinfo_from_text(text)
    except Exception:
        # fallback heuristic
        basic_info = basicinfo_from_text(text)

    return {"text": text, "basic_info": basic_info}
