"""FastAPI application for the ATS Resume Scorer web interface."""

from __future__ import annotations

import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

load_dotenv()

from api.config import UPLOAD_DIR
from api.routes import generate, jd, providers, rescore, score, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)


app = FastAPI(
    title="ATS Resume Scorer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(score.router, prefix="/api")
app.include_router(jd.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(rescore.router, prefix="/api")
app.include_router(providers.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
