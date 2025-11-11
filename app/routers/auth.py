from fastapi import APIRouter, Depends, HTTPException
from ..models import User
from ..db import get_session
from ..security import get_password_hash, verify_password, create_access_token
from sqlmodel import select
from pydantic import BaseModel
from ..config import settings

# If Supabase is configured, expose a route to validate Supabase token
if settings.SUPABASE_URL:
    from ..auth_supabase import get_current_user as get_supabase_user

router = APIRouter(prefix="/auth", tags=["auth"])


class UserIn(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(payload: UserIn, session=Depends(get_session)):
    q = session.exec(select(User).where(User.username == payload.username)).first()
    if q:
        raise HTTPException(status_code=400, detail="User exists")
    user = User(username=payload.username, hashed_password=get_password_hash(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(user.id)
    return {"access_token": token}


@router.post("/login")
def login(payload: UserIn, session=Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    return {"access_token": token}


if settings.SUPABASE_URL:
    @router.get("/me")
    async def me(current_user=Depends(get_supabase_user)):
        # return the supabase user info obtained from the auth endpoint
        return current_user
