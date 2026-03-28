"""Main FastAPI application for the Swan Interaction Overlay."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from saa.sio.api.routes import router
from saa.sio.api.websocket import ws_router

app = FastAPI(
    title="Swan Interaction Overlay",
    description="Human-facing interface for Swan Affective Architecture",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)
