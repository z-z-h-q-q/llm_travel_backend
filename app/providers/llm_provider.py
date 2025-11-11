import httpx
from ..config import settings
from typing import Any


async def coza_plan_request(prompt: str) -> Any:
    """Call the Coza orchestrated agent. Returns parsed plan JSON.
    Expects COZA_AGENT_URL and COZA_API_KEY in env.
    """
    if not settings.COZA_AGENT_URL:
        raise RuntimeError("COZA_AGENT_URL not configured")

    headers = {"Authorization": f"Bearer {settings.COZA_API_KEY}"} if settings.COZA_API_KEY else {}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.COZA_AGENT_URL, json={"prompt": prompt}, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def plan_by_coza(basic_info: dict) -> dict:
    # Build a prompt for the agent
    prompt = f"Generate a TravelPlan JSON matching the schema given BasicInfo: {basic_info}"
    data = await coza_plan_request(prompt)
    # Expect data to be plan-compatible; caller should validate
    return data
