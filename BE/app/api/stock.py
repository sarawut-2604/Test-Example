"""Stock event audit routes."""

from typing import Optional

from fastapi import APIRouter, Query

from app.models.schemas import StockEvent, Store
from app.repositories.db import db
from app.services.stock import StockService

router = APIRouter(tags=["stock", "stores"])


@router.get("/stock-events", response_model=list[StockEvent])
def list_stock_events(
    meal_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[StockEvent]:
    return StockService(db).list_events(meal_id=meal_id, limit=limit)


@router.get("/stores", response_model=list[Store])
def list_stores() -> list[Store]:
    return list(db.stores.values())


@router.post("/dev/reset")
def reset_data() -> dict:
    """Reset in-memory DB to seed state — useful while debugging."""
    db.reset()
    return {"ok": True, "message": "Database reset to seed data"}
