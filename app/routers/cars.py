from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.car import CarListResponse
from app.services.car_service import get_cars

router = APIRouter(prefix="/cars", tags=["cars"])


@router.get("", response_model=CarListResponse, status_code=200)
def list_cars(
    brand: Optional[str] = Query(None, description="Filter by exact brand (case-sensitive)"),
    year: Optional[int] = Query(None, description="Filter by manufacturing year"),
    price: Optional[float] = Query(None, description="Filter by exact price"),
) -> CarListResponse:
    """Return all cars from the local JSON file, with optional filtering.

    Supports filtering by ``brand``, ``year``, and ``price`` query parameters.
    When multiple filters are provided, they are combined using logical AND.

    Args:
        brand: Exact brand to filter by (case-sensitive).
        year: Manufacturing year to filter by.
        price: Exact price to filter by.

    Returns:
        A CarListResponse containing the matching cars and total count.

    Raises:
        HTTPException 500: If the data file cannot be read.
    """
    try:
        return get_cars(brand=brand, year=year, price=price)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500, detail=f"Car data file not found: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to load car data: {exc}"
        ) from exc
