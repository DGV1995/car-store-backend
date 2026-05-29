from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.models.car import Car, CarListResponse

# Path to the local JSON data file
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CARS_JSON_PATH = DATA_DIR / "cars.json"


def _load_cars_from_json() -> list[dict]:
    """Load all car records from the local JSON file.

    Returns:
        A list of raw dicts from the JSON file, or an empty list if the file
        does not exist or is malformed.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
    """
    if not CARS_JSON_PATH.exists():
        raise FileNotFoundError(f"Car data file not found: {CARS_JSON_PATH}")
    with open(CARS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Support both a top-level list and a dict with a "cars" key
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("cars", data.get("data", []))
    return []


def get_cars(
    brand: Optional[str] = None,
    year: Optional[int] = None,
    price: Optional[float] = None,
) -> CarListResponse:
    """Retrieve cars from the JSON file with optional filtering.

    All filters are combined using logical AND. When no filters are provided,
    all cars are returned.

    Args:
        brand: Exact brand to filter by (case-sensitive).
        year: Manufacturing year to filter by.
        price: Exact price to filter by.

    Returns:
        A CarListResponse containing the matching cars and total count.
    """
    raw_cars = _load_cars_from_json()

    # Convert to Car models for validation
    cars: list[Car] = [Car(**item) for item in raw_cars]

    # Apply filters (all combined with AND)
    if brand is not None:
        cars = [c for c in cars if c.brand == brand]
    if year is not None:
        cars = [c for c in cars if c.year == year]
    if price is not None:
        cars = [c for c in cars if c.price == price]

    return CarListResponse(cars=cars, total=len(cars))
