"""In-memory data store — no external DB required for the challenge."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models.schemas import (
    Meal,
    Order,
    OrderStatus,
    StockEvent,
    StockEventSource,
    StockEventType,
    Store,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryDB:
    """Simple mutable store shared across the app lifespan."""

    def __init__(self) -> None:
        self.stores: dict[str, Store] = {}
        self.meals: dict[str, Meal] = {}
        # user_id -> meal_id -> quantity
        self.carts: dict[str, dict[str, int]] = {}
        self.orders: dict[str, Order] = {}
        self.stock_events: list[StockEvent] = []
        self._order_seq = 1000
        self.seed()

    def seed(self) -> None:
        stores = [
            Store(id="store_1", name="Green Bowl Silom", region="th"),
            Store(id="store_2", name="Bakery Lane Sukhumvit", region="th"),
        ]
        for s in stores:
            self.stores[s.id] = s

        meals = [
            Meal(
                id="meal_1",
                store_id="store_1",
                name="Surplus Biriyani Bowl",
                description="Veggie bowl rescued at closing time",
                original_price=180.0,
                discounted_price=79.0,
                stock_available=10,
            ),
            Meal(
                id="meal_2",
                store_id="store_1",
                name="Chicken Rice Box",
                description="Half portion left from lunch rush",
                original_price=120.0,
                discounted_price=55.0,
                stock_available=5,
            ),
            Meal(
                id="meal_3",
                store_id="store_2",
                name="Assorted Pastry Pack",
                description="Croissants & buns — bake of the day leftovers",
                original_price=250.0,
                discounted_price=99.0,
                stock_available=8,
            ),
            Meal(
                id="meal_4",
                store_id="store_2",
                name="Sandwich Surprise",
                description="Mixed sandwiches, surprise filling",
                original_price=150.0,
                discounted_price=65.0,
                stock_available=3,
                is_published=False,
            ),
        ]
        for m in meals:
            self.meals[m.id] = m

        # Empty cart for demo user
        self.carts["user_demo_1"] = {}

    def reset(self) -> None:
        self.__init__()

    def next_order_number(self) -> str:
        self._order_seq += 1
        return f"SF-{self._order_seq}"

    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"

    def append_stock_event(
        self,
        *,
        meal_id: str,
        store_id: str,
        event_type: StockEventType,
        event_source: StockEventSource,
        quantity: int,
        stock_before: int,
        stock_after: int,
        reference_id: Optional[str] = None,
        note: str = "",
    ) -> StockEvent:
        event = StockEvent(
            id=self.new_id("se"),
            meal_id=meal_id,
            store_id=store_id,
            event_type=event_type,
            event_source=event_source,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            reference_id=reference_id,
            note=note,
            created_at=_now(),
        )
        self.stock_events.append(event)
        return event

    def snapshot(self) -> dict:
        return {
            "meals": {k: v.model_dump() for k, v in self.meals.items()},
            "carts": deepcopy(self.carts),
            "orders": {k: v.model_dump() for k, v in self.orders.items()},
            "stock_events": [e.model_dump() for e in self.stock_events],
        }


db = InMemoryDB()
