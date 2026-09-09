"""Cart routes."""

from fastapi import APIRouter

from app.models.schemas import CartAddRequest, CartResponse, CartUpdateRequest
from app.repositories.db import db
from app.services.cart import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
def get_cart() -> CartResponse:
    return CartService(db).get_cart()


@router.post("/items", response_model=CartResponse)
def add_to_cart(payload: CartAddRequest) -> CartResponse:
    return CartService(db).add_item(payload)


@router.patch("/items/{meal_id}", response_model=CartResponse)
def update_cart_item(meal_id: str, payload: CartUpdateRequest) -> CartResponse:
    return CartService(db).update_item(meal_id, payload)


@router.delete("", response_model=CartResponse)
def clear_cart() -> CartResponse:
    return CartService(db).clear()
