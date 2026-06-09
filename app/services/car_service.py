from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from app.models.car import Car, CarCreate, CarFilter

DATA_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = DATA_DIR / "cars.json"
UPLOADS_DIR = DATA_DIR / "uploads"


def _ensure_dirs() -> None:
    """Ensure the uploads directory and cars.json exist."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _load_cars() -> list[dict]:
    """Load all cars from the JSON file."""
    _ensure_dirs()
    try:
        raw = DATA_FILE.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_cars(cars: list[dict]) -> None:
    """Persist the list of cars to the JSON file."""
    _ensure_dirs()
    DATA_FILE.write_text(
        json.dumps(cars, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _next_id(cars: list[dict]) -> int:
    """Return the next available auto-increment ID."""
    if not cars:
        return 1
    return max(c["id"] for c in cars) + 1


def save_upload_image(file_bytes: bytes, original_filename: str) -> str:
    """Save an uploaded image to the uploads folder and return the relative URL."""
    _ensure_dirs()
    ext = Path(original_filename).suffix if original_filename else ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOADS_DIR / unique_name
    file_path.write_bytes(file_bytes)
    return f"/uploads/{unique_name}"


def get_cars(filters: CarFilter | None = None) -> list[Car]:
    """Return cars optionally filtered by query parameters (AND logic)."""
    data = _load_cars()
    cars = [Car(**item) for item in data]

    if filters is None:
        return cars

    result = []
    for car in cars:
        if filters.brand is not None and car.brand.lower() != filters.brand.lower():
            continue
        if filters.year_min is not None and car.year < filters.year_min:
            continue
        if filters.year_max is not None and car.year > filters.year_max:
            continue
        if filters.price_min is not None and car.price < filters.price_min:
            continue
        if filters.price_max is not None and car.price > filters.price_max:
            continue
        result.append(car)

    return result


def create_car(car_data: CarCreate, image_url: str) -> Car:
    """Add a new car to the JSON store and return it with an assigned ID."""
    data = _load_cars()
    new_id = _next_id(data)

    new_item = {
        "id": new_id,
        "image_url": image_url,
        "brand": car_data.brand,
        "model": car_data.model,
        "year": car_data.year,
        "price": car_data.price,
    }
    data.append(new_item)
    _save_cars(data)
    return Car(**new_item)
