"""Order routes."""

from fastapi import APIRouter

from app.models.schemas import Order, OrderCreateResponse
from app.repositories.db import db
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[Order])
def list_orders() -> list[Order]:
    return OrderService(db).list_orders()


@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    return OrderService(db).get_order(order_id)


@router.post("", response_model=OrderCreateResponse, status_code=201)
def create_order() -> OrderCreateResponse:
    """Checkout the current cart into a confirmed order."""
    return OrderService(db).create_from_cart()


@router.post("/{order_id}/cancel", response_model=Order)
def cancel_order(order_id: str) -> Order:
    return OrderService(db).cancel(order_id)


@router.post("/{order_id}/complete", response_model=Order)
def complete_order(order_id: str) -> Order:
    return OrderService(db).complete(order_id)
