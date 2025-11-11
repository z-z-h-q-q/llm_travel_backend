from fastapi import APIRouter, HTTPException
from ..providers.llm_provider import plan_by_coza
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["ai"])


class AIRequest(BaseModel):
    basic_info: dict


@router.post("/plan")
async def generate_plan(req: AIRequest):
    try:
        plan = await plan_by_coza(req.basic_info)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
