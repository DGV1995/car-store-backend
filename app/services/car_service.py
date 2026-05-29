from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.models.car import Car, CarCreate, CarListResponse

# Path to the local JSON data file
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CARS_JSON_PATH = DATA_DIR / "cars.json"

# Path to uploaded images
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _ensure_dirs() -> None:
    """Create required directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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


def _save_cars_to_json(cars: list[dict]) -> None:
    """Write the full list of car dicts to the JSON file."""
    _ensure_dirs()
    with open(CARS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cars, f, indent=2)


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


def create_car(car_data: CarCreate, image_url: str) -> Car:
    """Create a new car listing and persist it to the JSON file.

    Args:
        car_data: The validated car data (brand, model, year, price).
        image_url: The URL path to the uploaded image.

    Returns:
        The newly created Car object with assigned ID.

    Raises:
        FileNotFoundError: If the data file cannot be found.
    """
    _ensure_dirs()

    # Load existing cars or start with an empty list
    try:
        raw_cars = _load_cars_from_json()
    except FileNotFoundError:
        raw_cars = []

    # Compute the next available ID
    next_id = max((car["id"] for car in raw_cars), default=0) + 1

    # Build the new car record
    new_car = Car(
        id=next_id,
        brand=car_data.brand,
        model=car_data.model,
        year=car_data.year,
        price=car_data.price,
        image_url=image_url,
    )

    # Append and persist
    raw_cars.append(new_car.model_dump())
    _save_cars_to_json(raw_cars)

    return new_car
