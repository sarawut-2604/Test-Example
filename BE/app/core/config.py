"""App configuration for the surplus-food mini API."""

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Surplus Food API"
    region: str = "th"
    # Simulated "current user" for the challenge (no real auth).
    default_user_id: str = "user_demo_1"


settings = Settings()
