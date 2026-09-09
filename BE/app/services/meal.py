"""Meal domain service."""

from fastapi import HTTPException

from app.models.schemas import Meal, MealCreate
from app.repositories.db import InMemoryDB


class MealService:
    def __init__(self, db: InMemoryDB) -> None:
        self.db = db

    def list_meals(self, *, published_only: bool = True) -> list[Meal]:
        meals = list(self.db.meals.values())
        if published_only:
            meals = [m for m in meals if m.is_published]
        return meals

    def get_meal(self, meal_id: str) -> Meal:
        meal = self.db.meals.get(meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail=f"Meal {meal_id} not found")
        return meal

    def create_meal(self, payload: MealCreate) -> Meal:
        if payload.store_id not in self.db.stores:
            raise HTTPException(status_code=400, detail="Unknown store_id")
        if payload.discounted_price > payload.original_price:
            raise HTTPException(
                status_code=400,
                detail="discounted_price cannot exceed original_price",
            )
        meal = Meal(id=self.db.new_id("meal"), **payload.model_dump())
        self.db.meals[meal.id] = meal
        return meal

    def adjust_stock_merchant(
        self, meal_id: str, delta: int, note: str = ""
    ) -> Meal:
        """Merchant restock / manual adjustment. Positive delta = add stock."""
        from app.models.schemas import StockEventSource, StockEventType
        from app.services.stock import StockService

        meal = self.get_meal(meal_id)
        stock = StockService(self.db)
        if delta >= 0:
            stock.apply(
                meal_id=meal.id,
                quantity=delta,
                event_type=StockEventType.INCREMENT,
                event_source=StockEventSource.MERCHANT,
                note=note or "merchant restock",
            )
        else:
            stock.apply(
                meal_id=meal.id,
                quantity=abs(delta),
                event_type=StockEventType.DECREMENT,
                event_source=StockEventSource.MERCHANT,
                note=note or "merchant reduction",
            )
        return self.get_meal(meal_id)
