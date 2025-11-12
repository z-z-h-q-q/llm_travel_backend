import httpx
from ..config import settings


async def route_between_points(origin: tuple, destination: tuple) -> dict:
    """Call Amap (高德) 路线接口，返回 route info.
    origin/destination are (lng, lat)
    """
    if not settings.AMAP_KEY:
        raise RuntimeError("AMAP_KEY not configured")

    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": settings.AMAP_KEY,
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def search_places(keyword: str, city: str | None = None, limit: int = 10) -> dict:
    """Search POI by text using Amap Place Search API.
    Returns the parsed JSON from Amap. Caller should handle empty results.
    """
    if not settings.AMAP_KEY:
        raise RuntimeError("AMAP_KEY not configured")

    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": settings.AMAP_KEY,
        "keywords": keyword,
        "offset": limit,
        "extensions": "all"
    }
    if city:
        params["city"] = city

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
