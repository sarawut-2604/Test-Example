"""Surplus-food marketplace API for the coding challenge."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cart, meals, orders, stock
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Surplus-food marketplace API: meals, cart, orders, stock events.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

region_prefix = f"/v1/{settings.region}"
app.include_router(meals.router, prefix=region_prefix)
app.include_router(cart.router, prefix=region_prefix)
app.include_router(orders.router, prefix=region_prefix)
app.include_router(stock.router, prefix=region_prefix)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
