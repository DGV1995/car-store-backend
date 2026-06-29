"""
app/main.py — FastAPI application entrypoint.

Configures CORS, mounts static file serving for uploads,
and includes all API routers.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.cars import router as cars_router
from app.routers.chat import router as chat_router

app = FastAPI(
    title="Car Store API",
    description="Backend API for the Car Store application.",
    version="0.1.0",
)

# ---- CORS configuration ----
# Allow requests from the frontend development server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Static file serving for uploaded images ----
# Mount the uploads directory at /uploads so image URLs resolve correctly.
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ---- API routers ----
app.include_router(cars_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
