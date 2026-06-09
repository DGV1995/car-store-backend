from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.routers.cars import router as cars_router

app = FastAPI(title="Car Store API", version="0.1.0")

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(cars_router)

# ── Static file serving for uploaded images ─────────────────────────
# Allow override via UPLOADS_DIR env var so tests can point to a temp directory.
_uploads_path_str = os.environ.get(
    "UPLOADS_DIR",
    str(Path(__file__).resolve().parent / "uploads"),
)
uploads_path = Path(_uploads_path_str)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
