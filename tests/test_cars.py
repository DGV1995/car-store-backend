from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Path to test data
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CARS_JSON_PATH = DATA_DIR / "cars.json"

# Path to uploads directory
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"


@pytest.fixture(autouse=True)
def _backup_and_restore_data():
    """Backup cars.json before each test and restore it after.

    Also cleans up any files created in uploads/ during the test.
    """
    # Backup the original data
    original_data = CARS_JSON_PATH.read_text() if CARS_JSON_PATH.exists() else "[]"
    original_upload_files = set(UPLOADS_DIR.iterdir()) if UPLOADS_DIR.exists() else set()

    yield

    # Restore the original data
    CARS_JSON_PATH.write_text(original_data)

    # Remove any files created during the test
    if UPLOADS_DIR.exists():
        current_files = set(UPLOADS_DIR.iterdir())
        for f in current_files - original_upload_files:
            f.unlink()


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c


def _load_test_cars() -> list[dict]:
    with open(CARS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _create_test_image(format: str = "jpeg") -> io.BytesIO:
    """Create a minimal valid image in memory for testing.

    Args:
        format: Image format ("jpeg", "png", "gif", "webp").

    Returns:
        A BytesIO stream containing image bytes.
    """
    # Minimal JPEG file (valid header + EOI marker)
    if format == "jpeg":
        data = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9])
    elif format == "png":
        data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0x60, 0x60, 0x60, 0x00, 0x00, 0x00, 0x04, 0x00, 0x01, 0x27, 0x34, 0x27, 0x1C, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82])
    elif format == "gif":
        data = bytes([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x00, 0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x4C, 0x01, 0x00, 0x3B])
    elif format == "webp":
        data = bytes([0x52, 0x49, 0x46, 0x46, 0x1A, 0x00, 0x00, 0x00, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50, 0x38, 0x20, 0x0E, 0x00, 0x00, 0x00, 0x2F, 0x00, 0x00, 0x00, 0x00, 0x10, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00])
    else:
        data = b"fake-image-content"

    return io.BytesIO(data)


class TestListCars:
    """Tests for GET /cars endpoint."""

    def test_get_all_cars(self, client):
        """AC 2: Without query parameters, returns all cars with HTTP 200."""
        all_cars = _load_test_cars()
        response = client.get("/cars")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(all_cars)
        assert len(data["cars"]) == len(all_cars)
        assert data["cars"] == all_cars

    def test_filter_by_brand(self, client):
        """AC 3: When brand query param is provided, returns only cars with that brand."""
        response = client.get("/cars", params={"brand": "Toyota"})
        assert response.status_code == 200
        data = response.json()
        assert all(car["brand"] == "Toyota" for car in data["cars"])
        assert data["total"] == 2  # Toyota Camry + Toyota Corolla

    def test_filter_by_brand_case_sensitive(self, client):
        """AC 3: Brand filtering is case-sensitive."""
        response = client.get("/cars", params={"brand": "toyota"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["cars"] == []

    def test_filter_by_year(self, client):
        """AC 4: When year query param is provided, returns only cars with that year."""
        response = client.get("/cars", params={"year": 2020})
        assert response.status_code == 200
        data = response.json()
        assert all(car["year"] == 2020 for car in data["cars"])
        assert data["total"] == 3  # Toyota Camry, Honda Civic, BMW X5 (2020)

    def test_filter_by_price(self, client):
        """AC 5: When price query param is provided, returns only cars with that price."""
        response = client.get("/cars", params={"price": 55000.0})
        assert response.status_code == 200
        data = response.json()
        assert all(car["price"] == 55000.0 for car in data["cars"])
        assert data["total"] == 1  # BMW X5 2022

    def test_filter_by_brand_and_year(self, client):
        """AC 6: When multiple filters are provided, returns cars matching all criteria."""
        response = client.get("/cars", params={"brand": "BMW", "year": 2020})
        assert response.status_code == 200
        data = response.json()
        assert len(data["cars"]) == 1
        car = data["cars"][0]
        assert car["brand"] == "BMW"
        assert car["year"] == 2020
        assert car["price"] == 52000.0
        assert data["total"] == 1

    def test_filter_by_all_params(self, client):
        """AC 6: When all three filters are provided, AND combination."""
        response = client.get(
            "/cars", params={"brand": "Toyota", "year": 2020, "price": 24000.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["cars"]) == 1
        car = data["cars"][0]
        assert car["brand"] == "Toyota"
        assert car["year"] == 2020
        assert car["price"] == 24000.0
        assert data["total"] == 1

    def test_filter_no_matches(self, client):
        """AC 6: Returns empty list if no matches."""
        response = client.get("/cars", params={"brand": "Ferrari"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["cars"] == []

    def test_filter_multiple_no_matches(self, client):
        """AC 6: Multiple filters with no matches returns empty list."""
        response = client.get(
            "/cars", params={"brand": "Toyota", "year": 2025}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["cars"] == []

    def test_health_endpoint(self, client):
        """Verify the health check endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_cars_endpoint_accepts_params_as_query_string(self, client):
        """Verify query parameters work via query string syntax."""
        response = client.get("/cars?brand=Honda")
        assert response.status_code == 200
        data = response.json()
        assert all(car["brand"] == "Honda" for car in data["cars"])

    def test_response_has_correct_structure(self, client):
        """Verify the response structure matches CarListResponse."""
        response = client.get("/cars")
        assert response.status_code == 200
        data = response.json()
        assert "cars" in data
        assert "total" in data
        assert isinstance(data["cars"], list)
        assert isinstance(data["total"], int)
        if data["cars"]:
            first = data["cars"][0]
            assert "id" in first
            assert "brand" in first
            assert "model" in first
            assert "year" in first
            assert "price" in first
            assert "image_url" in first


class TestCreateCar:
    """Tests for POST /cars endpoint."""

    def test_create_car_success(self, client):
        """AC 5: Returns HTTP 201 with the created Car object."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "Tesla",
                "model": "Model 3",
                "year": 2023,
                "price": 45000.0,
            },
            files={"image": ("test.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 201
        car = response.json()
        assert car["brand"] == "Tesla"
        assert car["model"] == "Model 3"
        assert car["year"] == 2023
        assert car["price"] == 45000.0
        assert car["id"] == 6  # 5 existing cars, so next ID is 6
        assert car["image_url"].startswith("/uploads/")
        assert car["image_url"].endswith(".jpg")

        # Verify the car was persisted
        all_cars = _load_test_cars()
        created = next((c for c in all_cars if c["id"] == 6), None)
        assert created is not None
        assert created["brand"] == "Tesla"
        assert created["model"] == "Model 3"
        assert created["image_url"].startswith("/uploads/")

    def test_create_car_missing_brand(self, client):
        """AC 2: Returns HTTP 422 when brand is missing."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "model": "Model 3",
                "year": 2023,
                "price": 45000.0,
            },
            files={"image": ("test.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 422

    def test_create_car_invalid_year(self, client):
        """AC 2: Returns HTTP 422 when year is invalid (future year)."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "Tesla",
                "model": "Model 3",
                "year": 2099,
                "price": 45000.0,
            },
            files={"image": ("test.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 422

    def test_create_car_invalid_price(self, client):
        """AC 2: Returns HTTP 422 when price is negative."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "Tesla",
                "model": "Model 3",
                "year": 2023,
                "price": -100.0,
            },
            files={"image": ("test.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 422

    def test_create_car_missing_image(self, client):
        """AC 2: Returns HTTP 422 when image file is missing."""
        response = client.post(
            "/cars",
            data={
                "brand": "Tesla",
                "model": "Model 3",
                "year": 2023,
                "price": 45000.0,
            },
        )
        assert response.status_code == 422

    def test_create_car_unsupported_image_type(self, client):
        """AC 2: Returns HTTP 422 for unsupported file type."""
        response = client.post(
            "/cars",
            data={
                "brand": "Tesla",
                "model": "Model 3",
                "year": 2023,
                "price": 45000.0,
            },
            files={"image": ("test.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 422

    def test_uploaded_image_served_statically(self, client):
        """AC 6: Uploaded images are accessible via browser at the URL."""
        image_data = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "Audi",
                "model": "A4",
                "year": 2022,
                "price": 35000.0,
            },
            files={"image": ("audi.jpg", image_data, "image/jpeg")},
        )
        assert response.status_code == 201
        car = response.json()
        image_url = car["image_url"]

        # Fetch the image via the static mount
        image_response = client.get(image_url)
        assert image_response.status_code == 200
        content_type = image_response.headers.get("content-type", "")
        assert content_type.startswith("image/")

    def test_image_with_png_format(self, client):
        """Verify PNG images are accepted and served correctly."""
        image = _create_test_image(format="png")
        response = client.post(
            "/cars",
            data={
                "brand": "Ford",
                "model": "Mustang",
                "year": 2023,
                "price": 55000.0,
            },
            files={"image": ("mustang.png", image, "image/png")},
        )
        assert response.status_code == 201
        car = response.json()
        assert car["image_url"].endswith(".png")

        # Fetch the image
        image_response = client.get(car["image_url"])
        assert image_response.status_code == 200
        assert "image/png" in image_response.headers.get("content-type", "")

    def test_image_with_gif_format(self, client):
        """Verify GIF images are accepted."""
        image = _create_test_image(format="gif")
        response = client.post(
            "/cars",
            data={
                "brand": "Chevrolet",
                "model": "Camaro",
                "year": 2022,
                "price": 42000.0,
            },
            files={"image": ("camaro.gif", image, "image/gif")},
        )
        assert response.status_code == 201
        car = response.json()
        assert car["image_url"].endswith(".gif")

    def test_create_car_empty_brand(self, client):
        """AC 2: Returns HTTP 422 when brand is empty string."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "",
                "model": "Model 3",
                "year": 2023,
                "price": 45000.0,
            },
            files={"image": ("test.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 422

    def test_create_car_price_as_string_number(self, client):
        """AC 2: Price can be sent as a string that parses to a number."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "Nissan",
                "model": "Altima",
                "year": 2023,
                "price": "28000",
            },
            files={"image": ("nissan.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 201
        car = response.json()
        assert car["price"] == 28000.0

    def test_create_car_year_as_string_number(self, client):
        """AC 2: Year can be sent as a string that parses to an int."""
        image = _create_test_image(format="jpeg")
        response = client.post(
            "/cars",
            data={
                "brand": "Hyundai",
                "model": "Elantra",
                "year": "2022",
                "price": 22000.0,
            },
            files={"image": ("hyundai.jpg", image, "image/jpeg")},
        )
        assert response.status_code == 201
        car = response.json()
        assert car["year"] == 2022

    def test_create_multiple_cars_increases_id(self, client):
        """Verify sequential IDs are assigned when creating multiple cars."""
        ids = []
        for i in range(3):
            image = _create_test_image(format="jpeg")
            response = client.post(
                "/cars",
                data={
                    "brand": "Test",
                    "model": f"Car-{i}",
                    "year": 2023,
                    "price": float(20000 + i * 1000),
                },
                files={"image": (f"test{i}.jpg", image, "image/jpeg")},
            )
            assert response.status_code == 201
            ids.append(response.json()["id"])

        # IDs should be sequential: 6, 7, 8 (after the 5 existing cars)
        assert ids == [6, 7, 8]
        assert len(set(ids)) == 3

    def test_create_car_webp_format(self, client):
        """Verify WebP images are accepted."""
        image = _create_test_image(format="webp")
        response = client.post(
            "/cars",
            data={
                "brand": "Volkswagen",
                "model": "Golf",
                "year": 2023,
                "price": 30000.0,
            },
            files={"image": ("golf.webp", image, "image/webp")},
        )
        assert response.status_code == 201
        car = response.json()
        assert car["image_url"].endswith(".webp")

        image_response = client.get(car["image_url"])
        assert image_response.status_code == 200
