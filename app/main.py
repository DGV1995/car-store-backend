from __future__ import annotations

from fastapi import FastAPI

from app.routers.cars import router as cars_router

app = FastAPI(
    title="Car Store API",
    description="A REST API for managing car listings.",
    version="0.1.0",
)

app.include_router(cars_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}
