from typing import Any
from ..utils import basicinfo_from_text


async def recognize_iflytek(audio_bytes: bytes, fmt: str = "wav") -> str:
    """iFlyTek integration has been removed from this deployment.

    This helper previously called the iFlyTek IAT service. To keep the
    codebase clean and avoid unexpected calls to a removed external
    provider, this function now raises a RuntimeError with a clear
    explanation and guidance for callers.
    """
    raise RuntimeError(
        "iFlyTek speech recognition integration has been removed. "
        "Please use client-side Web Speech API for recognition or configure "
        "an alternative speech recognition service and update the backend accordingly."
    )


async def transcribe_and_extract_basicinfo(audio_bytes: bytes, fmt: str = "wav") -> dict:
    """Deprecated: previously transcribed audio via iFlyTek then extracted basic info.

    Now this function will raise a RuntimeError to indicate that audio-based
    transcription is not available. Callers should instead send text to the
    AI parsing endpoint.
    """
    raise RuntimeError(
        "Audio transcription is not available on the server. "
        "Use browser Web Speech API to obtain text and send the text for parsing."
    )
