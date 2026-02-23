"""
Async httpx client wrapper for the Omnidesk API.
Uses HTTP Basic Auth with the configured staff email and API key.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from src.config import settings


def make_omnidesk_client() -> httpx.AsyncClient:
    cfg = settings.omnidesk
    return httpx.AsyncClient(
        base_url=cfg.base_url,
        auth=(cfg.staff_email, cfg.api_key.get_secret_value()),
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )


@asynccontextmanager
async def lifespan_omnidesk_client() -> AsyncIterator[httpx.AsyncClient]:
    """Used in the FastAPI lifespan to keep a single client alive."""
    async with make_omnidesk_client() as client:
        yield client
