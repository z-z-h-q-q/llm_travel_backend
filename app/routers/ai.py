from fastapi import APIRouter, HTTPException
from ..providers.llm_provider import plan_by_coza
from pydantic import BaseModel
from ..providers.llm_provider import parse_basicinfo_with_xinghuo
from ..schemas import BasicInfo

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


class ParseTextRequest(BaseModel):
    text: str


@router.post('/parse_basicinfo', response_model=BasicInfo)
async def parse_basicinfo(req: ParseTextRequest):
    try:
        basic = await parse_basicinfo_with_xinghuo(req.text)
        # validate with BasicInfo model
        info = BasicInfo.parse_obj(basic)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
