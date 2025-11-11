import httpx
from ..config import settings
from typing import Any, List


def _headers():
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
    return {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }


async def list_plans(user_id: str) -> List[Any]:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans"
    params = {"owner_id": f"eq.{user_id}"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


async def create_plan(user_id: str, payload: dict) -> Any:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans"
    body = {**payload, "owner_id": user_id}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=_headers(), json=body)
        resp.raise_for_status()
        return resp.json()


async def update_plan(plan_id: int, user_id: str, payload: dict) -> Any:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans?id=eq.{plan_id}&owner_id=eq.{user_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.patch(url, headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()


async def delete_plan(plan_id: int, user_id: str) -> Any:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans?id=eq.{plan_id}&owner_id=eq.{user_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(url, headers=_headers())
        resp.raise_for_status()
        return {"ok": True}
