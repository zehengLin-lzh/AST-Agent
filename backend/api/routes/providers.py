"""Provider and model listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from src.llm.client import get_providers_info

router = APIRouter()


@router.get("/providers")
async def list_providers():
    return get_providers_info()
