from pydantic import BaseModel
from typing import List, Optional, Any


class BasicInfo(BaseModel):
    departure: Optional[str]
    destination: str
    # The following fields are required to be present in the JSON payload
    # but may be null when unknown. Declaring them as Optional without a
    # default makes them required keys that accept null values.
    travelers: Optional[int]
    startDate: Optional[str]
    endDate: Optional[str]
    days: Optional[int]
    # Optional fields
    preferences: Optional[List[str]]
    budget: Optional[float]


class DestinationIntro(BaseModel):
    overview: Optional[str] = ""
    weather: Optional[str] = ""
    culture: Optional[str] = ""


class Attraction(BaseModel):
    name: str
    address: Optional[str]
    description: Optional[str]
    ticket_price: Optional[float]
    estimated_visit_time: Optional[str]


class Accommodation(BaseModel):
    name: str
    address: Optional[str]
    cost: Optional[float]


class MealInfo(BaseModel):
    name: Optional[str]
    description: Optional[str]
    cost: Optional[float]


class DayMeals(BaseModel):
    breakfast: Optional[MealInfo] = None
    lunch: Optional[MealInfo] = None
    dinner: Optional[MealInfo] = None


class DayPlan(BaseModel):
    day: int
    date: str
    accommodation: Optional[Accommodation]
    attractions: List[Attraction]
    meals: Optional[DayMeals]


class TotalBudget(BaseModel):
    attractions: float
    hotels: float
    meals: float
    total: float


class Summary(BaseModel):
    total_days: int
    total_budget: TotalBudget
    suggestions: List[str]


class TravelPlan(BaseModel):
    title: str
    basic_info: BasicInfo
    destination_intro: DestinationIntro
    daily_plan: List[DayPlan]
    summary: Summary


class TravelPlanOut(TravelPlan):
    id: int
    createdAt: Optional[str]
    updatedAt: Optional[str]
