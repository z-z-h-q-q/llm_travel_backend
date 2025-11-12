import httpx
import logging
from ..config import settings
from typing import Any, List

logger = logging.getLogger(__name__)


def _headers():
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
    return {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        # Ensure PostgREST (Supabase) returns the representation of inserted/updated rows
        # instead of returning no content (204). This makes resp.json() safe to call.
        "Prefer": "return=representation"
    }


async def list_plans(user_id: str) -> List[Any]:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans"
    params = {"owner_id": f"eq.{user_id}"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        rows = resp.json()
        # Unwrap 'data' JSON column to match local DB format: {id, ...data}
        out = []
        for r in rows:
            data = r.get("data") or {}
            # ensure dict
            if not isinstance(data, dict):
                data = {}
            out.append({"id": r.get("id"), **data})
        return out


async def create_plan(user_id: str, payload: dict) -> Any:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans"
    # Supabase table expects a 'data' json column and a title/owner_id columns.
    body = {"owner_id": user_id, "title": payload.get("title"), "data": payload}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=_headers(), json=body)
        try:
            resp.raise_for_status()
        except Exception:
            # Log response body for easier debugging
            logger.exception("Supabase create_plan HTTP error: status=%s body=%s", resp.status_code, resp.text)
            raise

        # Some Supabase/PostgREST instances may return an empty body on success;
        # defensively handle non-JSON or empty responses.
        text = resp.text or ""
        if not text.strip():
            logger.warning("Supabase create returned empty body (status=%s). Returning synthesized row.", resp.status_code)
            # synthesize a returned row using payload stored in 'data' column
            data = body.get("data") or {}
            return [{"id": None, **(data if isinstance(data, dict) else {})}]

        rows = resp.json()
        # Supabase returns array of inserted rows; unwrap data column
        out = []
        for r in rows:
            data = r.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            out.append({"id": r.get("id"), **data})
        return out


async def update_plan(plan_id: int, user_id: str, payload: dict) -> Any:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans?id=eq.{plan_id}&owner_id=eq.{user_id}"
    # Patch the 'data' JSON column and optionally title
    body = {"data": payload}
    if "title" in payload:
        body["title"] = payload.get("title")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.patch(url, headers=_headers(), json=body)
        try:
            resp.raise_for_status()
        except Exception:
            logger.exception("Supabase update_plan HTTP error: status=%s body=%s", resp.status_code, resp.text)
            raise

        text = resp.text or ""
        if not text.strip():
            logger.warning("Supabase update returned empty body (status=%s). Returning synthesized row.", resp.status_code)
            data = body.get("data") or {}
            return [{"id": plan_id, **(data if isinstance(data, dict) else {})}]

        rows = resp.json()
        out = []
        for r in rows:
            data = r.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            out.append({"id": r.get("id"), **data})
        return out


async def delete_plan(plan_id: int, user_id: str) -> Any:
    url = f"{settings.SUPABASE_URL}/rest/v1/travel_plans?id=eq.{plan_id}&owner_id=eq.{user_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(url, headers=_headers())
        resp.raise_for_status()
        return {"ok": True}
