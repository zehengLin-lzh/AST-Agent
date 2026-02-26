"""Job description fetch endpoint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.scorer.jd_fetcher import fetch_jd_from_url

router = APIRouter()


class FetchJDRequest(BaseModel):
    url: str


@router.post("/fetch-jd")
async def fetch_jd(req: FetchJDRequest):
    try:
        text = await asyncio.to_thread(fetch_jd_from_url, req.url)
        return {"text": text}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(502, str(exc)) from exc
