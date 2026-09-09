"""Meal routes."""

from fastapi import APIRouter, Query

from app.models.schemas import Meal, MealCreate
from app.repositories.db import db
from app.services.meal import MealService

router = APIRouter(prefix="/meals", tags=["meals"])


@router.get("", response_model=list[Meal])
def list_meals(published_only: bool = Query(default=True)) -> list[Meal]:
    return MealService(db).list_meals(published_only=published_only)


@router.get("/{meal_id}", response_model=Meal)
def get_meal(meal_id: str) -> Meal:
    return MealService(db).get_meal(meal_id)


@router.post("", response_model=Meal, status_code=201)
def create_meal(payload: MealCreate) -> Meal:
    return MealService(db).create_meal(payload)


@router.post("/{meal_id}/stock-adjust", response_model=Meal)
def adjust_stock(meal_id: str, delta: int, note: str = "") -> Meal:
    """Merchant/admin stock adjustment. Positive = restock, negative = reduce."""
    return MealService(db).adjust_stock_merchant(meal_id, delta, note)
