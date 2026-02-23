from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.omnidesk_bot.omnidesk import make_omnidesk_client
from src.omnidesk_bot.routers.cases import router as cases_router
from inh_accounts_sdk import inh_accounts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fetch JWKS from InNoHassle Accounts so the SDK can verify tokens
    await inh_accounts.update_key_set()

    # Keep a single Omnidesk client alive for the process lifetime
    async with make_omnidesk_client() as client:
        app.state.omnidesk_client = client
        yield


app = FastAPI(
    title="Omnidesk Portal API",
    description="Authenticated proxy between the customer portal and Omnidesk",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # TODO: tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
