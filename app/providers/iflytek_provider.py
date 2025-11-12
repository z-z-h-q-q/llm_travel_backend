import base64
import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlparse, quote
from email.utils import formatdate

import httpx
import logging

from ..config import settings


async def extract_basicinfo_with_iflytek(text: str) -> dict:
    """Call iFlyTek large model to extract BasicInfo from free-form text.
    Expects settings.XUNFEI_LLM_URL to be configured to accept a JSON payload like:
      {"input": "<text>", "task": "extract_basic_info"}
    and return JSON {"basic_info": {...}}.

    This function is kept for LLM extraction (not the IAT service). Keep as-is.
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


def _make_iflytek_auth(api_key: str, api_secret: str, url: str, method: str = "POST") -> (str, str):
    """Construct the authorization and date parameters required by iFlyTek IAT.

    Returns (authorization_param, date_str)
    """
    parsed = urlparse(url)
    host = parsed.netloc
    # RFC1123 date string (GMT)
    date = formatdate(usegmt=True)

    path = parsed.path or "/v1"
    request_line = f"{method} {path} HTTP/1.1"

    signature_origin = f"host: {host}\ndate: {date}\n{request_line}"

    signature_sha = hmac.new(api_secret.encode("utf-8"), signature_origin.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode()

    authorization_origin = f'api_key="{api_key}",algorithm="hmac-sha256",headers="host date request-line",signature="{signature}"'
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    return authorization, date


def make_iflytek_ws_url(api_key: str, api_secret: str, base_url: str = None) -> str:
    """Construct a signed wss URL for iFlyTek IAT websocket connections.

    Returns the full URL including authorization and date query params.
    """
    # Default to the official ws-api v2 host to match demo flows.
    if not base_url:
        base_url = "wss://ws-api.xfyun.cn/v2/iat"

    # Use GET for request-line
    authorization, date = _make_iflytek_auth(api_key, api_secret, base_url, method="GET")
    from urllib.parse import quote as _quote
    parsed = urlparse(base_url)
    host = parsed.netloc
    return f"{base_url}?authorization={_quote(authorization, safe='')}&date={_quote(date, safe='')}&host={_quote(host, safe='')}"

async def recognize_iat_ws_v2(audio_bytes: bytes, fmt: str = "pcm", sample_rate: int = 16000, timeout: int = 30) -> str:
    """Use the official ws-api.xfyun.cn v2/iat single-frame flow (matches the provided demo).
    Build a signed wss URL for ws-api.xfyun.cn/v2/iat, send a single message containing
    'common', 'business' and 'data' with status=2 (final), then wait for recognition result.
    """
    # Use the official ws-api v2 host used in the demo (ws-api.xfyun.cn).
    # Do not reuse the REST `XUNFEI_SPEECH_RECOGNITION_URL` (which points to iat.xf-yun.com)
    # because the v2 WS host is different. Allow overriding via XUNFEI_WS_RECOGNITION_URL if provided.
    base_ws = getattr(settings, 'XUNFEI_SPEECH_RECOGNITION_URL', '') or "wss://ws-api.xfyun.cn/v2/iat"
    # Ensure scheme is ws/wss
    if base_ws.startswith("https://"):
        base_ws = "wss://" + base_ws[len("https://"):]
    if base_ws.startswith("http://"):
        base_ws = "ws://" + base_ws[len("http://"):]

    # If a user supplied a different path (e.g., /v1), normalize to /v2/iat for this flow
    parsed = urlparse(base_ws)
    if not parsed.path or not parsed.path.startswith("/v2"):
        # replace path with /v2/iat
        base_ws = f"{parsed.scheme}://{parsed.netloc}/v2/iat"

    if not settings.XUNFEI_API_KEY or not settings.XUNFEI_API_SECRET or not settings.XUNFEI_APPID:
        raise RuntimeError("XUNFEI credentials/appid not configured for ws v2 flow")

    ws_url = make_iflytek_ws_url(settings.XUNFEI_API_KEY, settings.XUNFEI_API_SECRET, base_ws)

    # Build the v2 message: include common (app_id), business args and data
    audio_b64 = base64.b64encode(audio_bytes).decode()
    msg = {
        "common": {"app_id": settings.XUNFEI_APPID},
        "business": {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo": 1, "vad_eos": 10000},
        "data": {"status": 2, "format": "audio/L16;rate=16000", "audio": audio_b64, "encoding": "raw"}
    }

    import websockets, asyncio
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
            await ws.send(json.dumps(msg))
            # Wait for responses until we get final result
            try:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    try:
                        data = json.loads(raw)
                    except Exception:
                        continue

                    # official v2 format: top-level 'code' and 'data.result.ws'
                    code = data.get("code")
                    if code is not None and code != 0:
                        raise RuntimeError(f"iFlyTek v2 error code={code} message={data.get('message')}")

                    result_ws = None
                    try:
                        result_ws = data.get("data", {}).get("result", {}).get("ws")
                    except Exception:
                        result_ws = None

                    if result_ws:
                        words = []
                        for seg in result_ws:
                            for cw in seg.get("cw", []):
                                w = cw.get("w")
                                if w:
                                    words.append(w)
                        joined = "".join(words)
                        # The demo prints results as they come; we return the first assembled text
                        return joined
            except asyncio.TimeoutError:
                raise RuntimeError("Timeout waiting for iFlyTek v2 websocket response")
    except Exception as e:
        raise RuntimeError(f"iFlyTek v2 websocket failed: {e}")
