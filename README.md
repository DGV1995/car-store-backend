# Car Store Backend

FastAPI backend for the Car Store application.

## Getting Started

1. Ensure Python 3.11+ and [uv](https://docs.astral.sh/uv/) are installed.
2. Sync dependencies:
   ```bash
   uv sync
   ```
3. (Optional) Create the required directories:
   ```bash
   mkdir -p data uploads
   ```
4. Run the server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.

## API Endpoints

| Method | Path            | Description                    |
|--------|-----------------|--------------------------------|
| GET    | `/api/cars`     | List all cars                  |
| POST   | `/api/cars`     | Create a new car (multipart)   |
| GET    | `/uploads/{fn}` | Serve uploaded car images      |

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entrypoint
│   ├── models.py         # Pydantic data models
│   ├── routers/
│   │   ├── __init__.py
│   │   └── cars.py       # Car API routes
│   └── services/
│       ├── __init__.py
│       └── file_service.py  # JSON file persistence
├── data/
│   └── cars.json         # Persistent car storage
├── uploads/              # Uploaded images directory
├── pyproject.toml
├── .gitignore
└── README.md
```
