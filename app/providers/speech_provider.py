import httpx
from ..config import settings
from typing import Any
from ..utils import basicinfo_from_text
from .iflytek_provider import (
    extract_basicinfo_with_iflytek,
    recognize_iat_ws_v2,
)


async def recognize_iflytek(audio_bytes: bytes, fmt: str = "wav") -> str:
    """Attempt to transcribe audio using configured iFlyTek speech endpoint.
    Prefer direct iFlyTek REST signing call when API credentials are present (XUNFEI_API_KEY and XUNFEI_API_SECRET).
    Otherwise, if settings.XUNFEI_SPEECH_RECOGNITION_URL is set, POST multipart/form-data with 'audio' to that URL.
    Otherwise raise RuntimeError.
    """
    # If API key/secret are configured, use the websocket v2 single-frame flow exclusively.
    # This avoids REST signing/endpoint differences and matches the official demo.
    if settings.XUNFEI_API_KEY and settings.XUNFEI_API_SECRET:
        # map common extensions to encoding hint
        ext = fmt.lower().strip()
        if ext in ("wav", "pcm"):
            fmt_hint = "pcm"
        elif ext in ("mp3", "lame"):
            fmt_hint = "mp3"
        else:
            fmt_hint = "pcm"
        # Use WS v2 flow; let errors propagate so caller can see upstream errors.
        return await recognize_iat_ws_v2(audio_bytes, fmt=fmt_hint)

    # Fallback: call a proxy/upload URL if configured
    if not settings.XUNFEI_SPEECH_RECOGNITION_URL:
        raise RuntimeError("XUNFEI_SPEECH_RECOGNITION_URL not configured and no API secret for direct iFlyTek call")

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
