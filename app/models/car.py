from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Car(BaseModel):
    """Car entity representing a vehicle listing."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="Unique identifier for the car")
    brand: str = Field(..., min_length=1, description="Car manufacturer (e.g., Toyota, BMW)")
    model: str = Field(..., min_length=1, description="Car model name (e.g., Camry, X5)")
    year: int = Field(..., ge=1886, description="Manufacturing year of the car")
    price: float = Field(..., gt=0, description="Price of the car in the base currency")
    image_url: str = Field(..., min_length=1, description="URL pointing to the car's image")


class CarCreate(BaseModel):
    """Request body for creating a new car listing. Excludes the image file upload."""

    brand: str = Field(..., min_length=1, description="Car manufacturer (e.g., Toyota, BMW)")
    model: str = Field(..., min_length=1, description="Car model name (e.g., Camry, X5)")
    year: int = Field(..., ge=1886, description="Manufacturing year of the car")
    price: float = Field(..., gt=0, description="Price of the car in the base currency")

    @field_validator("year")
    @classmethod
    def year_not_in_future(cls, v: int) -> int:
        max_year = datetime.now().year + 1
        if v > max_year:
            raise ValueError(f"year cannot be later than {max_year}")
        return v


class CarListResponse(BaseModel):
    """Wrapper for a list of Car objects in API responses."""

    cars: list[Car] = Field(..., description="List of car listings")
    total: int = Field(..., ge=0, description="Total number of cars matching the query")
