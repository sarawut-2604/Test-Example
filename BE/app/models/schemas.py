"""Pydantic models for the surplus-food domain."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StockEventType(str, Enum):
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"


class StockEventSource(str, Enum):
    USER = "USER"  # customer cart / order
    MERCHANT = "MERCHANT"  # store restock / adjustment
    SYSTEM = "SYSTEM"  # cancel restore, admin tools


class Store(BaseModel):
    id: str
    name: str
    region: str = "th"


class Meal(BaseModel):
    id: str
    store_id: str
    name: str
    description: str = ""
    # Surplus discount: customers pay discounted_price
    original_price: float
    discounted_price: float
    stock_available: int
    is_published: bool = True


class MealCreate(BaseModel):
    store_id: str
    name: str
    description: str = ""
    original_price: float
    discounted_price: float
    stock_available: int = 0
    is_published: bool = True


class CartItem(BaseModel):
    meal_id: str
    quantity: int
    unit_price: float
    meal_name: str
    line_total: float


class CartResponse(BaseModel):
    user_id: str
    items: list[CartItem]
    item_count: int
    subtotal: float


class CartAddRequest(BaseModel):
    meal_id: str
    quantity: int = Field(ge=1, default=1)


class CartUpdateRequest(BaseModel):
    quantity: int = Field(ge=0)


class StockEvent(BaseModel):
    id: str
    meal_id: str
    store_id: str
    event_type: StockEventType
    event_source: StockEventSource
    quantity: int
    stock_before: int
    stock_after: int
    reference_id: Optional[str] = None  # cart line / order id
    note: str = ""
    created_at: datetime


class OrderLine(BaseModel):
    meal_id: str
    meal_name: str
    quantity: int
    unit_price: float
    line_total: float


class Order(BaseModel):
    id: str
    order_number: str
    user_id: str
    status: OrderStatus
    lines: list[OrderLine]
    subtotal: float
    created_at: datetime
    updated_at: datetime


class OrderCreateResponse(BaseModel):
    order: Order
    message: str
