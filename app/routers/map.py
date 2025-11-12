from fastapi import APIRouter, HTTPException
from ..providers.map_provider import route_between_points
from pydantic import BaseModel
from ..providers.map_provider import search_places

router = APIRouter(prefix="/map", tags=["map"])


class RouteReq(BaseModel):
    origin: list
    destination: list


@router.post("/route")
async def get_route(req: RouteReq):
    try:
        origin = tuple(req.origin)
        dest = tuple(req.destination)
        return await route_between_points(origin, dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/places/search')
async def places_search(keyword: str, city: str | None = None, limit: int = 10):
    """Proxy to Amap place/text search. Returns Amap JSON or raises 500 on error."""
    try:
        result = await search_places(keyword, city, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
