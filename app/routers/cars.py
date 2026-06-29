"""
app/routers/cars.py — Car API endpoints.

Provides:
- GET /api/cars — list all cars
- POST /api/cars — create a new car with image upload
"""

import json
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models import Car, CarListResponse, CarResponse

router = APIRouter(prefix="/api/cars", tags=["cars"])

# Paths
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "cars.json"
UPLOADS_DIR = Path("uploads")

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure data file exists
if not DATA_FILE.exists():
    DATA_FILE.write_text("[]", encoding="utf-8")


# ---------- helpers ----------


def _load_cars() -> List[dict]:
    """Load all car records from the JSON data file."""
    try:
        content = DATA_FILE.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_cars(cars: List[dict]) -> None:
    """Persist all car records to the JSON data file."""
    DATA_FILE.write_text(
        json.dumps(cars, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------- endpoints ----------


@router.get("", response_model=CarListResponse, status_code=status.HTTP_200_OK)
async def list_cars() -> CarListResponse:
    """
    Retrieve all cars.

    Returns a list of all car records stored in the persistent JSON file.
    """
    raw_cars = _load_cars()
    cars = [Car(**item) for item in raw_cars]
    return CarListResponse(cars=cars)


@router.post("", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def create_car(
    image: UploadFile = File(..., description="Car image file."),
    brand: str = Form(..., min_length=1, description="Car manufacturer/brand name."),
    model: str = Form(..., min_length=1, description="Car model name."),
    year: int = Form(..., ge=1886, description="Manufacturing year."),
    km: int = Form(..., ge=0, description="Total kilometres driven."),
    price: float = Form(..., ge=0.0, description="Price in EUR."),
) -> CarResponse:
    """
    Create a new car.

    Accepts multipart/form-data with an image file and car details.
    The image is saved to the uploads/ directory and the car record
    is persisted to data/cars.json.
    """
    # Generate a unique ID for the car
    car_id = str(uuid.uuid4())

    # Determine file extension from the uploaded image
    original_filename = image.filename or "image.jpg"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        ext = ".jpg"  # fallback extension

    # Build the image filename and URL
    image_filename = f"{car_id}{ext}"
    image_url = f"/uploads/{image_filename}"

    # Save the image to disk
    image_path = UPLOADS_DIR / image_filename
    content = await image.read()
    image_path.write_bytes(content)

    # Build the car record
    car_data = {
        "id": car_id,
        "brand": brand.strip(),
        "model": model.strip(),
        "year": year,
        "km": km,
        "price": price,
        "image_url": image_url,
    }

    # Validate via Pydantic before persisting
    car = Car(**car_data)

    # Persist to JSON file
    raw_cars = _load_cars()
    raw_cars.append(car.model_dump())
    _save_cars(raw_cars)

    return CarResponse(car=car)
