"""
main.py — FastAPI application entry point.

Configures CORS, static file serving, and includes the cars router.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.cars import router as cars_router

app = FastAPI(
    title="Car Store API",
    description="A simple API for managing a car store inventory.",
    version="1.0.0",
)

# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Static files (uploads) ----------

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ---------- Routers ----------

app.include_router(cars_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}
