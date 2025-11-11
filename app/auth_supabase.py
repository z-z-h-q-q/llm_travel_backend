from fastapi import Header, HTTPException
import httpx
from .config import settings


async def get_current_user(authorization: str = Header(None)):
    """Validate Supabase JWT by calling Supabase /auth/v1/user endpoint.
    Requires the frontend to pass the Supabase access token as Authorization: Bearer <token>
    Returns user dict with at least 'id' field.
    """
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    url = f"{settings.SUPABASE_URL}/auth/v1/user"
    headers = {
        "Authorization": authorization,
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or ""
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return resp.json()
