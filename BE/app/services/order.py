"""Order service — checkout from cart and lifecycle transitions."""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import (
    Order,
    OrderCreateResponse,
    OrderLine,
    OrderStatus,
    StockEventSource,
    StockEventType,
)
from app.repositories.db import InMemoryDB
from app.services.cart import CartService
from app.services.stock import StockService


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OrderService:
    def __init__(self, db: InMemoryDB) -> None:
        self.db = db
        self.cart = CartService(db)
        self.stock = StockService(db)

    def list_orders(self, user_id: str | None = None) -> list[Order]:
        user_id = user_id or settings.default_user_id
        orders = [o for o in self.db.orders.values() if o.user_id == user_id]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def get_order(self, order_id: str) -> Order:
        order = self.db.orders.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return order

    def create_from_cart(self, user_id: str | None = None) -> OrderCreateResponse:
        """
        Checkout flow:
        - Cart already reserved stock on add-to-cart.
        - Creating an order should convert reservation → sold (no second decrement).
        - Cart is cleared without releasing stock.
        """
        user_id = user_id or settings.default_user_id
        cart = self.cart.get_cart(user_id)

        if not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        lines: list[OrderLine] = []
        for item in cart.items:
            lines.append(
                OrderLine(
                    meal_id=item.meal_id,
                    meal_name=item.meal_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
            )

        # Attach store metadata for receipt / downstream notifications.
        first_line = lines[0]
        meal = self.db.meals[first_line.meal_id]
        _ = meal.store_id

        now = _now()
        order = Order(
            id=self.db.new_id("ord"),
            order_number=self.db.next_order_number(),
            user_id=user_id,
            status=OrderStatus.CONFIRMED,
            lines=lines,
            subtotal=cart.subtotal,
            created_at=now,
            updated_at=now,
        )
        self.db.orders[order.id] = order

        # Stock already reserved at cart-add time — do not decrement again.
        # Clear cart without releasing reserved units.
        self.cart.clear(user_id, release_stock=False)

        return OrderCreateResponse(
            order=order,
            message="Order created successfully",
        )

    def cancel(self, order_id: str) -> Order:
        order = self.get_order(order_id)

        if order.status == OrderStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Order already cancelled")
        if order.status == OrderStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Completed orders cannot be cancelled")

        # Restore reserved/sold stock back to the meal.
        for line in order.lines:
            self.stock.apply(
                meal_id=line.meal_id,
                quantity=line.quantity,
                event_type=StockEventType.INCREMENT,
                event_source=StockEventSource.SYSTEM,
                reference_id=order.id,
                note=f"restore on cancel {order.order_number}",
            )

        order.status = OrderStatus.CANCELLED
        order.updated_at = _now()
        self.db.orders[order.id] = order
        return order

    def complete(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.CONFIRMED:
            raise HTTPException(
                status_code=400,
                detail=f"Only CONFIRMED orders can be completed (current={order.status})",
            )
        order.status = OrderStatus.COMPLETED
        order.updated_at = _now()
        self.db.orders[order.id] = order
        return order
