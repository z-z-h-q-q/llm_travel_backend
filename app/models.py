from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from sqlalchemy import Column, JSON
import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # use sa_column if you need unique constraint at the DB level
    username: str = Field(index=True)
    hashed_password: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class TravelPlanModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(index=True)
    title: str
    data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
