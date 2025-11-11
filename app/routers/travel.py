from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..schemas import TravelPlan
from ..models import TravelPlanModel
from ..db import get_session
from sqlmodel import select
from pydantic import BaseModel
from ..config import settings

router = APIRouter(prefix="/travel", tags=["travel"])


class CreatePlanIn(BaseModel):
    title: str
    basic_info: dict
    destination_intro: dict = {}
    daily_plan: list = []
    summary: dict = {}


if settings.SUPABASE_URL:
    # Supabase-backed async endpoints
    from ..providers.supabase_client import list_plans as sb_list_plans, create_plan as sb_create_plan, update_plan as sb_update_plan, delete_plan as sb_delete_plan
    from ..auth_supabase import get_current_user


    @router.get("/plans")
    async def list_plans(current_user=Depends(get_current_user)):
        user_id = current_user.get("id")
        return await sb_list_plans(user_id)


    @router.post("/plans")
    async def create_plan(payload: CreatePlanIn, current_user=Depends(get_current_user)):
        user_id = current_user.get("id")
        # Supabase returns an array of inserted rows
        created = await sb_create_plan(user_id, payload.dict())
        return created


    @router.put("/plans/{plan_id}")
    async def update_plan(plan_id: int, payload: dict, current_user=Depends(get_current_user)):
        user_id = current_user.get("id")
        updated = await sb_update_plan(plan_id, user_id, payload)
        return updated


    @router.delete("/plans/{plan_id}")
    async def delete_plan(plan_id: int, current_user=Depends(get_current_user)):
        user_id = current_user.get("id")
        return await sb_delete_plan(plan_id, user_id)

else:
    # Fallback to local DB (synchronous)

    @router.get("/plans")
    def list_plans(session=Depends(get_session)):
        q = session.exec(select(TravelPlanModel)).all()
        return [{"id": p.id, **p.data} for p in q]


    @router.post("/plans")
    def create_plan(payload: CreatePlanIn, session=Depends(get_session)):
        plan = TravelPlanModel(owner_id=0, title=payload.title, data=payload.dict())
        session.add(plan)
        session.commit()
        session.refresh(plan)
        return {"id": plan.id, **plan.data}


    @router.put("/plans/{plan_id}")
    def update_plan(plan_id: int, payload: dict, session=Depends(get_session)):
        p = session.get(TravelPlanModel, plan_id)
        if not p:
            raise HTTPException(status_code=404, detail="Not found")
        p.data = payload
        session.add(p)
        session.commit()
        session.refresh(p)
        return {"id": p.id, **p.data}


    @router.delete("/plans/{plan_id}")
    def delete_plan(plan_id: int, session=Depends(get_session)):
        p = session.get(TravelPlanModel, plan_id)
        if not p:
            raise HTTPException(status_code=404, detail="Not found")
        session.delete(p)
        session.commit()
        return {"ok": True}
