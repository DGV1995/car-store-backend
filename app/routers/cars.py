from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.models.car import Car, CarListResponse
from app.services.car_service import create_car, get_cars
from app.services.car_service import UPLOADS_DIR as UPLOADS_DIR

router = APIRouter(prefix="/cars", tags=["cars"])

# Allowed image MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


def _validate_and_save_image(image: UploadFile) -> str:
    """Validate and save an uploaded image file.

    Args:
        image: The uploaded image file.

    Returns:
        The URL path to the saved image (e.g. "/uploads/abc.jpg").

    Raises:
        HTTPException 422: If the file type is invalid or saving fails.
    """
    if image.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{image.content_type}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}.",
        )

    # Determine file extension from content type
    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }[image.content_type]

    # Generate a unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOADS_DIR / unique_name

    # Save the file
    try:
        content = image.file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded image: {exc}"
        ) from exc

    return f"/uploads/{unique_name}"


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


@router.post("", response_model=Car, status_code=201)
def add_car(
    brand: str = Form(..., min_length=1, description="Car manufacturer"),
    model: str = Form(..., min_length=1, description="Car model"),
    year: int = Form(..., description="Manufacturing year"),
    price: float = Form(..., gt=0, description="Price in base currency"),
    image: UploadFile = File(..., description="Car image file"),
) -> Car:
    """Create a new car listing with an image upload.

    Accepts multipart form data with fields ``brand``, ``model``, ``year``,
    ``price``, and ``image`` (file). The image is saved to the local
    ``uploads/`` directory and its URL is stored in the car record.

    Args:
        brand: Car manufacturer (e.g., Toyota, BMW).
        model: Car model name (e.g., Camry, X5).
        year: Manufacturing year (>= 1886).
        price: Price in base currency (> 0).
        image: The car image file (JPEG, PNG, GIF, or WebP).

    Returns:
        The created Car object with assigned ID and image URL.

    Raises:
        HTTPException 422: If validation fails or file type is unsupported.
        HTTPException 500: If image saving or data persistence fails.
    """
    # --- Validate text fields via CarCreate rules ---
    # Reuse CarCreate's validators by constructing it from the form fields
    from app.models.car import CarCreate

    try:
        car_data = CarCreate(brand=brand, model=model, year=year, price=price)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # --- Validate and save image ---
    image_url = _validate_and_save_image(image)

    # --- Persist car ---
    try:
        return create_car(car_data, image_url)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to create car listing: {exc}"
        ) from exc
