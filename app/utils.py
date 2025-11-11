from typing import Any


def basicinfo_from_text(text: str) -> dict:
    """A tiny heuristic parser to extract minimal BasicInfo from text if LLM not available.
    Prefer using LLM in production.
    """
    # This is a placeholder. In real use, call an LLM to parse free text to BasicInfo.
    return {"destination": text, "travelers": 1, "startDate": "", "endDate": "", "days": 1, "preferences": [], "budget": 0}
