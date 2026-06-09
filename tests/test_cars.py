from __future__ import annotations

import importlib
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Create a TestClient with isolated temp directories for data and uploads.

    The fixture monkeypatches service-level paths and sets ``UPLOADS_DIR``
    so that the ``main`` module mounts its ``/uploads`` static directory
    at the temp path.  ``main`` is reloaded via ``importlib.reload`` to
    ensure the mount picks up the environment-variable override.
    """
    from app.services import car_service
    from app.services.car_service import DATA_FILE, UPLOADS_DIR

    test_data_file = tmp_path / "cars.json"
    test_uploads_dir = tmp_path / "uploads"
    test_uploads_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(car_service, "DATA_FILE", test_data_file)
    monkeypatch.setattr(car_service, "UPLOADS_DIR", test_uploads_dir)
    monkeypatch.setattr(car_service, "DATA_DIR", tmp_path)

    # Write initial empty cars.json
    test_data_file.write_text("[]", encoding="utf-8")

    # Set env var so main.py picks up the temp uploads dir via importlib.reload
    monkeypatch.setenv("UPLOADS_DIR", str(test_uploads_dir))

    # Reload main so the StaticFiles mount uses the temp directory
    import main as main_module

    main_module = importlib.reload(main_module)
    app = main_module.app

    with TestClient(app) as c:
        yield c


def _make_image_file(name: str = "test.jpg", content: bytes = b"fake-image-data") -> io.BytesIO:
    """Return a BytesIO object pretending to be an image file."""
    return io.BytesIO(content)


# ── GET /api/cars ────────────────────────────────────────────────────


def test_get_cars_empty(client: TestClient) -> None:
    """AC #2: GET returns empty list when no cars exist."""
    resp = client.get("/api/cars")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_cars_after_post(client: TestClient) -> None:
    """AC #1: GET returns list of all cars after posting one."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("test.jpg", img, "image/jpeg")},
        data={"brand": "Toyota", "model": "Corolla", "year": 2020, "price": 25000},
    )
    assert resp.status_code == 201
    created = resp.json()

    resp2 = client.get("/api/cars")
    assert resp2.status_code == 200
    data = resp2.json()
    assert len(data) == 1
    assert data[0]["id"] == created["id"]
    assert data[0]["brand"] == "Toyota"


# ── GET /api/cars with filters ───────────────────────────────────────


def test_get_cars_filter_brand(client: TestClient) -> None:
    """AC #1: Filter by brand (AND logic)."""
    # Insert two cars
    for brand, model, year, price in [
        ("Ford", "Focus", 2021, 22000),
        ("Toyota", "Corolla", 2020, 25000),
    ]:
        client.post(
            "/api/cars",
            files={"image": ("c.jpg", b"data", "image/jpeg")},
            data={"brand": brand, "model": model, "year": year, "price": price},
        )

    resp = client.get("/api/cars", params={"brand": "Ford"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["brand"] == "Ford"


def test_get_cars_filter_year_min(client: TestClient) -> None:
    """AC #1: Filter by year_min."""
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "A", "model": "M1", "year": 2019, "price": 10000},
    )
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "B", "model": "M2", "year": 2022, "price": 20000},
    )

    resp = client.get("/api/cars", params={"year_min": 2020})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["year"] == 2022


def test_get_cars_filter_year_max(client: TestClient) -> None:
    """AC #1: Filter by year_max."""
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "A", "model": "M1", "year": 2019, "price": 10000},
    )
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "B", "model": "M2", "year": 2022, "price": 20000},
    )

    resp = client.get("/api/cars", params={"year_max": 2020})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["year"] == 2019


def test_get_cars_filter_price_range(client: TestClient) -> None:
    """AC #1: Filter by price_min and price_max."""
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "A", "model": "M1", "year": 2020, "price": 5000},
    )
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "B", "model": "M2", "year": 2020, "price": 15000},
    )
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "C", "model": "M3", "year": 2020, "price": 30000},
    )

    resp = client.get("/api/cars", params={"price_min": 10000, "price_max": 20000})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["price"] == 15000


def test_get_cars_filter_and_logic(client: TestClient) -> None:
    """AC #1: Multiple filters combine with AND logic."""
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "Ford", "model": "Focus", "year": 2020, "price": 22000},
    )
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "Ford", "model": "Mustang", "year": 2022, "price": 35000},
    )
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "Toyota", "model": "Corolla", "year": 2020, "price": 25000},
    )

    # Ford, year >= 2021 -> should return Mustang only
    resp = client.get("/api/cars", params={"brand": "Ford", "year_min": 2021})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["model"] == "Mustang"


def test_get_cars_filter_no_match(client: TestClient) -> None:
    """AC #2: GET returns empty list if no cars match the filters."""
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", b"data", "image/jpeg")},
        data={"brand": "Ford", "model": "Focus", "year": 2020, "price": 22000},
    )

    resp = client.get("/api/cars", params={"brand": "Tesla"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── POST /api/cars ───────────────────────────────────────────────────


def test_post_cars_creates_car(client: TestClient) -> None:
    """AC #3: POST creates car with image upload, returns car object."""
    img = _make_image_file(name="mycar.jpg", content=b"\x89PNG\r\n\x1a\n")
    resp = client.post(
        "/api/cars",
        files={"image": ("mycar.jpg", img, "image/png")},
        data={"brand": "Tesla", "model": "Model 3", "year": 2023, "price": 45000},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["brand"] == "Tesla"
    assert body["model"] == "Model 3"
    assert body["year"] == 2023
    assert body["price"] == 45000
    assert isinstance(body["id"], int)
    assert body["id"] >= 1
    assert body["image_url"].startswith("/uploads/")
    assert body["image_url"].endswith(".jpg") or body["image_url"].endswith(".png")


def test_post_cars_saves_image_to_uploads(client: TestClient) -> None:
    """AC #3 + #6: Image is persisted in uploads/ directory."""
    img_data = b"fake-image-content"
    resp = client.post(
        "/api/cars",
        files={"image": ("car.png", io.BytesIO(img_data), "image/png")},
        data={"brand": "Honda", "model": "Civic", "year": 2021, "price": 24000},
    )
    assert resp.status_code == 201
    body = resp.json()
    # Extract the filename from image_url
    image_url: str = body["image_url"]
    filename = image_url.split("/")[-1]

    # Check the file exists in uploads (via the monkeypatched path)
    from app.services.car_service import UPLOADS_DIR

    saved_file = UPLOADS_DIR / filename
    assert saved_file.exists()
    assert saved_file.read_bytes() == img_data


def test_post_cars_auto_increments_id(client: TestClient) -> None:
    """AC #3: IDs are auto-incremented."""
    ids = []
    for i in range(3):
        resp = client.post(
            "/api/cars",
            files={"image": ("c.jpg", io.BytesIO(b"data"), "image/jpeg")},
            data={"brand": "B", "model": f"M{i}", "year": 2020, "price": 10000 * (i + 1)},
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])
    assert ids == [1, 2, 3]


# ── POST /api/cars validation errors ─────────────────────────────────


def test_post_cars_missing_brand(client: TestClient) -> None:
    """AC #4: Returns 422 when required field 'brand' is missing."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"model": "Model 3", "year": 2023, "price": 45000},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    # FastAPI/Form validation returns error details
    assert any("brand" in str(err) for err in (detail if isinstance(detail, list) else [detail]))


def test_post_cars_missing_model(client: TestClient) -> None:
    """AC #4: Returns 422 when required field 'model' is missing."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"brand": "Tesla", "year": 2023, "price": 45000},
    )
    assert resp.status_code == 422


def test_post_cars_missing_year(client: TestClient) -> None:
    """AC #4: Returns 422 when required field 'year' is missing."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"brand": "Tesla", "model": "Model 3", "price": 45000},
    )
    assert resp.status_code == 422


def test_post_cars_missing_price(client: TestClient) -> None:
    """AC #4: Returns 422 when required field 'price' is missing."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"brand": "Tesla", "model": "Model 3", "year": 2023},
    )
    assert resp.status_code == 422


def test_post_cars_year_out_of_range_low(client: TestClient) -> None:
    """AC #4: Returns 422 when year < 1886."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"brand": "Tesla", "model": "Model 3", "year": 1800, "price": 45000},
    )
    assert resp.status_code == 422


def test_post_cars_year_out_of_range_high(client: TestClient) -> None:
    """AC #4: Returns 422 when year > 2026."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"brand": "Tesla", "model": "Model 3", "year": 2030, "price": 45000},
    )
    assert resp.status_code == 422


def test_post_cars_negative_price(client: TestClient) -> None:
    """AC #4: Returns 422 when price is negative."""
    img = _make_image_file()
    resp = client.post(
        "/api/cars",
        files={"image": ("t.jpg", img, "image/jpeg")},
        data={"brand": "Tesla", "model": "Model 3", "year": 2023, "price": -100},
    )
    assert resp.status_code == 422


def test_post_cars_missing_image(client: TestClient) -> None:
    """AC #4: Returns 422 when image file is missing."""
    resp = client.post(
        "/api/cars",
        data={"brand": "Tesla", "model": "Model 3", "year": 2023, "price": 45000},
    )
    assert resp.status_code == 422


# ── CORS ─────────────────────────────────────────────────────────────


def test_cors_allowed_origin(client: TestClient) -> None:
    """AC #5: CORS allows requests from http://localhost:3000."""
    resp = client.get("/api/cars", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_other_origin(client: TestClient) -> None:
    """AC #5: CORS does not allow arbitrary origins."""
    resp = client.get("/api/cars", headers={"Origin": "https://evil.com"})
    # The request still succeeds but the ACAO header should NOT be set to evil.com
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers or resp.headers["access-control-allow-origin"] != "https://evil.com"


# ── Persistence ──────────────────────────────────────────────────────


def test_data_persistence(client: TestClient, tmp_path: Path) -> None:
    """AC #6: Data persists in cars.json between requests (simulated restarts)."""
    from app.services.car_service import DATA_FILE

    # Create a car
    img = _make_image_file()
    client.post(
        "/api/cars",
        files={"image": ("c.jpg", img, "image/jpeg")},
        data={"brand": "BMW", "model": "X5", "year": 2022, "price": 60000},
    )

    # Check the JSON file directly
    assert DATA_FILE.exists()
    raw = DATA_FILE.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert len(data) == 1
    assert data[0]["brand"] == "BMW"
    assert data[0]["model"] == "X5"

    # Uploaded image file exists
    from app.services.car_service import UPLOADS_DIR

    upload_files = list(UPLOADS_DIR.iterdir())
    assert len(upload_files) == 1


# ── Static file serving ──────────────────────────────────────────────


def test_uploaded_image_served_with_correct_content_type(client: TestClient) -> None:
    """AC #2: Uploaded JPEG image is served with correct Content-Type header."""
    img_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"  # JPEG magic bytes
    resp = client.post(
        "/api/cars",
        files={"image": ("test.jpg", io.BytesIO(img_data), "image/jpeg")},
        data={"brand": "Test", "model": "Car", "year": 2023, "price": 30000},
    )
    assert resp.status_code == 201
    image_url: str = resp.json()["image_url"]

    # Fetch the image via the static mount
    resp_img = client.get(image_url)
    assert resp_img.status_code == 200, f"Expected 200, got {resp_img.status_code} for {image_url}"
    assert resp_img.headers["content-type"] == "image/jpeg"


def test_uploaded_png_image_served_with_correct_content_type(client: TestClient) -> None:
    """AC #2: Uploaded PNG image is served with correct Content-Type header."""
    img_data = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes
    resp = client.post(
        "/api/cars",
        files={"image": ("test.png", io.BytesIO(img_data), "image/png")},
        data={"brand": "Test", "model": "Car", "year": 2023, "price": 30000},
    )
    assert resp.status_code == 201
    image_url: str = resp.json()["image_url"]

    # Fetch the image via the static mount
    resp_img = client.get(image_url)
    assert resp_img.status_code == 200, f"Expected 200, got {resp_img.status_code} for {image_url}"
    assert resp_img.headers["content-type"] == "image/png"


def test_uploaded_image_returns_image_bytes(client: TestClient) -> None:
    """AC #2: Uploaded image is served with the exact bytes that were uploaded."""
    img_data = b"my-original-image-bytes-content"
    resp = client.post(
        "/api/cars",
        files={"image": ("photo.jpg", io.BytesIO(img_data), "image/jpeg")},
        data={"brand": "Test", "model": "Car", "year": 2023, "price": 30000},
    )
    assert resp.status_code == 201
    image_url: str = resp.json()["image_url"]

    resp_img = client.get(image_url)
    assert resp_img.status_code == 200
    assert resp_img.content == img_data
