"""Cart service — holds reserved surplus meals before checkout."""

from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import (
    CartAddRequest,
    CartItem,
    CartResponse,
    CartUpdateRequest,
    StockEventSource,
    StockEventType,
)
from app.repositories.db import InMemoryDB
from app.services.meal import MealService
from app.services.stock import StockService


class CartService:
    def __init__(self, db: InMemoryDB) -> None:
        self.db = db
        self.meals = MealService(db)
        self.stock = StockService(db)

    def _user_cart(self, user_id: str) -> dict[str, int]:
        if user_id not in self.db.carts:
            self.db.carts[user_id] = {}
        return self.db.carts[user_id]

    def get_cart(self, user_id: str | None = None) -> CartResponse:
        user_id = user_id or settings.default_user_id
        raw = self._user_cart(user_id)
        items: list[CartItem] = []
        subtotal = 0.0

        for meal_id, quantity in raw.items():
            meal = self.meals.get_meal(meal_id)
            # Customers pay the surplus discounted price, not the original.
            unit_price = meal.discounted_price
            line_total = unit_price * quantity
            subtotal += line_total
            items.append(
                CartItem(
                    meal_id=meal_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    meal_name=meal.name,
                    line_total=line_total,
                )
            )

        return CartResponse(
            user_id=user_id,
            items=items,
            item_count=sum(i.quantity for i in items),
            subtotal=subtotal,
        )

    def add_item(self, payload: CartAddRequest, user_id: str | None = None) -> CartResponse:
        user_id = user_id or settings.default_user_id
        meal = self.meals.get_meal(payload.meal_id)

        if not meal.is_published:
            raise HTTPException(status_code=400, detail="Meal is not published")

        cart = self._user_cart(user_id)
        current_qty = cart.get(payload.meal_id, 0)

        # Reserve stock immediately when adding to cart (surplus marketplace pattern)
        self.stock.apply(
            meal_id=payload.meal_id,
            quantity=payload.quantity,
            event_type=StockEventType.DECREMENT,
            event_source=StockEventSource.USER,
            reference_id=f"cart:{user_id}",
            note="reserve on add-to-cart",
        )

        cart[payload.meal_id] = current_qty + payload.quantity
        return self.get_cart(user_id)

    def update_item(
        self,
        meal_id: str,
        payload: CartUpdateRequest,
        user_id: str | None = None,
    ) -> CartResponse:
        user_id = user_id or settings.default_user_id
        cart = self._user_cart(user_id)

        if meal_id not in cart:
            raise HTTPException(status_code=404, detail="Meal not in cart")

        old_qty = cart[meal_id]
        new_qty = payload.quantity
        delta = new_qty - old_qty

        if delta > 0:
            # Increasing the cart line reserves additional units.
            self.stock.apply(
                meal_id=meal_id,
                quantity=delta,
                event_type=StockEventType.DECREMENT,
                event_source=StockEventSource.USER,
                reference_id=f"cart:{user_id}",
                note="reserve on cart increase",
            )
        elif delta < 0:
            self.stock.apply(
                meal_id=meal_id,
                quantity=abs(delta),
                event_type=StockEventType.INCREMENT,
                event_source=StockEventSource.USER,
                reference_id=f"cart:{user_id}",
                note="release on cart decrease",
            )

        if new_qty == 0:
            del cart[meal_id]
        else:
            cart[meal_id] = new_qty

        return self.get_cart(user_id)

    def clear(self, user_id: str | None = None, *, release_stock: bool = True) -> CartResponse:
        user_id = user_id or settings.default_user_id
        cart = self._user_cart(user_id)

        if release_stock:
            for meal_id, quantity in list(cart.items()):
                self.stock.apply(
                    meal_id=meal_id,
                    quantity=quantity,
                    event_type=StockEventType.INCREMENT,
                    event_source=StockEventSource.USER,
                    reference_id=f"cart:{user_id}",
                    note="release on cart clear",
                )

        self.db.carts[user_id] = {}
        return self.get_cart(user_id)
