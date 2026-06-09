from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class CarBase(BaseModel):
    """Base model for a car listing."""
    image_url: str = Field(..., description="URL of the car image")
    brand: str = Field(..., description="Car brand/manufacturer name")
    model: str = Field(..., description="Car model name")
    year: int = Field(..., ge=1886, le=2026, description="Manufacturing year (1886-2026)")
    price: float = Field(..., ge=0.0, description="Price in USD (non-negative)")


class CarCreate(BaseModel):
    """Schema for creating a new car."""
    brand: str = Field(..., description="Car brand/manufacturer name")
    model: str = Field(..., description="Car model name")
    year: int = Field(..., ge=1886, le=2026, description="Manufacturing year (1886-2026)")
    price: float = Field(..., ge=0.0, description="Price in USD (non-negative)")


class Car(BaseModel):
    """Full car model including the database ID."""
    id: int = Field(..., description="Unique identifier for the car")
    image_url: str = Field(..., description="URL of the car image")
    brand: str = Field(..., description="Car brand/manufacturer name")
    model: str = Field(..., description="Car model name")
    year: int = Field(..., ge=1886, le=2026, description="Manufacturing year (1886-2026)")
    price: float = Field(..., ge=0.0, description="Price in USD (non-negative)")
    model_config = ConfigDict(from_attributes=True)


class CarFilter(BaseModel):
    """Filter request schema for querying cars."""
    brand: str | None = Field(None, description="Filter by brand name")
    year_min: int | None = Field(None, ge=1886, le=2026, description="Minimum manufacturing year")
    year_max: int | None = Field(None, ge=1886, le=2026, description="Maximum manufacturing year")
    price_min: float | None = Field(None, ge=0.0, description="Minimum price in USD")
    price_max: float | None = Field(None, ge=0.0, description="Maximum price in USD")
