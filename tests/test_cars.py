from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.car import Car, CarListResponse

# Path to test data
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CARS_JSON_PATH = DATA_DIR / "cars.json"


@pytest.fixture
@classmethod
def client():
    """Provide a TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c


def _load_test_cars() -> list[dict]:
    with open(CARS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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
