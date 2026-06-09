from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models.car import Car, CarCreate, CarFilter
from app.services.car_service import create_car, get_cars, save_upload_image

router = APIRouter(prefix="/api/cars", tags=["cars"])


@router.get("", response_model=list[Car])
def list_cars(
    brand: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
) -> list[Car]:
    """Return all cars, optionally filtered by query parameters (AND logic)."""
    filters = CarFilter(
        brand=brand,
        year_min=year_min,
        year_max=year_max,
        price_min=price_min,
        price_max=price_max,
    )
    return get_cars(filters)


@router.post("", response_model=Car, status_code=status.HTTP_201_CREATED)
async def add_car(
    image: UploadFile = File(..., description="Car image file"),
    brand: str = Form(..., description="Car brand/manufacturer name"),
    model: str = Form(..., description="Car model name"),
    year: int = Form(..., ge=1886, le=2026, description="Manufacturing year (1886-2026)"),
    price: float = Form(..., ge=0.0, description="Price in USD (non-negative)"),
) -> Car:
    """Add a new car with an image upload (multipart/form-data)."""
    if not image.filename or image.filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image file is required",
        )

    # Validate the image content type
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be an image",
        )

    image_bytes = await image.read()

    # Pydantic validation via CarCreate
    car_data = CarCreate(brand=brand, model=model, year=year, price=price)

    image_url = save_upload_image(image_bytes, image.filename)
    return create_car(car_data, image_url)
