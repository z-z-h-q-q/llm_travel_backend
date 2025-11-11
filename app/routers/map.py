from fastapi import APIRouter, HTTPException
from ..providers.map_provider import route_between_points
from pydantic import BaseModel

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
