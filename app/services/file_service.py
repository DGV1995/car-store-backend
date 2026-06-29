"""
app/services/file_service.py — JSON file persistence for car records.

Provides functions to read and write the list of cars from/to a JSON file.
"""

import json
import os
from typing import List

from app.models import Car

DATA_DIR = "data"
CARS_FILE = os.path.join(DATA_DIR, "cars.json")


def _ensure_data_file() -> None:
    """Create the data directory and cars.json file if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CARS_FILE):
        with open(CARS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def read_cars() -> List[Car]:
    """Read all cars from the JSON file.

    Returns:
        A list of Car objects. Returns an empty list if the file is missing or empty.
    """
    _ensure_data_file()
    try:
        with open(CARS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Car(**item) for item in data]
    except (json.JSONDecodeError, FileNotFoundError, IOError):
        return []


def write_cars(cars: List[Car]) -> None:
    """Write a list of cars to the JSON file.

    Args:
        cars: List of Car objects to persist.
    """
    _ensure_data_file()
    with open(CARS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            [car.model_dump() for car in cars],
            f,
            indent=2,
            ensure_ascii=False,
        )
