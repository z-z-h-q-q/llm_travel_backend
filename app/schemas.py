from pydantic import BaseModel
from typing import List, Optional, Any


class BasicInfo(BaseModel):
    departure: Optional[str]
    destination: str
    travelers: int
    startDate: str
    endDate: str
    days: int
    preferences: List[str]
    budget: float


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
    location: Optional[Any] = None


class Accommodation(BaseModel):
    name: str
    address: Optional[str]
    cost: Optional[float]


class MealInfo(BaseModel):
    name: Optional[str]
    description: Optional[str]
    cost: Optional[float]


class DayMeals(BaseModel):
    breakfast: MealInfo
    lunch: MealInfo
    dinner: MealInfo


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
