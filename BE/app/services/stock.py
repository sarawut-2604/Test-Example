"""Stock event application — source of truth for inventory mutations."""

from typing import Optional

from fastapi import HTTPException

from app.models.schemas import StockEvent, StockEventSource, StockEventType
from app.repositories.db import InMemoryDB


class StockService:
    def __init__(self, db: InMemoryDB) -> None:
        self.db = db

    def apply(
        self,
        *,
        meal_id: str,
        quantity: int,
        event_type: StockEventType,
        event_source: StockEventSource,
        reference_id: Optional[str] = None,
        note: str = "",
    ) -> StockEvent:
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="quantity must be > 0")

        meal = self.db.meals.get(meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail=f"Meal {meal_id} not found")

        stock_before = meal.stock_available

        if event_type == StockEventType.DECREMENT:
            if stock_before < quantity:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Insufficient stock",
                        "meal_id": meal_id,
                        "requested": quantity,
                        "available": stock_before,
                    },
                )
            stock_after = stock_before - quantity
        else:
            stock_after = stock_before + quantity

        meal.stock_available = stock_after
        self.db.meals[meal_id] = meal

        return self.db.append_stock_event(
            meal_id=meal_id,
            store_id=meal.store_id,
            event_type=event_type,
            event_source=event_source,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            reference_id=reference_id,
            note=note,
        )

    def list_events(
        self,
        *,
        meal_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[StockEvent]:
        events = list(reversed(self.db.stock_events))
        if meal_id:
            events = [e for e in events if e.meal_id == meal_id]
        return events[:limit]
