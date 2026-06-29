"""
app/routers/cars.py — Car API routes.

Endpoints:
- GET /api/cars — returns all cars from persistent storage.
- POST /api/cars — creates a new car with image upload.
"""

import os
import uuid
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models import Car, CarListResponse, CarResponse
from app.services.file_service import read_cars, write_cars

router = APIRouter(prefix="/api/cars", tags=["cars"])

UPLOADS_DIR = "uploads"


@router.get("", response_model=CarListResponse, status_code=status.HTTP_200_OK)
def get_cars():
    """Return all cars from persistent storage."""
    cars = read_cars()
    return CarListResponse(cars=cars)


@router.post("", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def create_car(
    image: UploadFile = File(..., description="Car image file"),
    brand: str = Form(..., min_length=1, description="Car manufacturer/brand name"),
    model: str = Form(..., min_length=1, description="Car model name"),
    year: int = Form(..., ge=1886, description="Manufacturing year"),
    km: int = Form(..., ge=0, description="Total kilometres driven"),
    price: float = Form(..., ge=0.0, description="Price in EUR"),
):
    """Create a new car with an uploaded image."""
    # Generate a unique ID for the car
    car_id = str(uuid.uuid4())

    # Determine file extension from the uploaded file
    original_filename = image.filename or "image.jpg"
    ext = os.path.splitext(original_filename)[1] or ".jpg"

    # Build a unique filename and save path
    saved_filename = f"{car_id}{ext}"
    saved_path = os.path.join(UPLOADS_DIR, saved_filename)

    # Ensure uploads directory exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Save the uploaded image to disk
    try:
        contents = await image.read()
        with open(saved_path, "wb") as f:
            f.write(contents)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save image: {exc}",
        )

    # Build the car record
    car = Car(
        id=car_id,
        brand=brand.strip(),
        model=model.strip(),
        year=year,
        km=km,
        price=price,
        image_url=f"/uploads/{saved_filename}",
    )

    # Persist the car record
    existing_cars = read_cars()
    existing_cars.append(car)
    write_cars(existing_cars)

    return CarResponse(car=car)
