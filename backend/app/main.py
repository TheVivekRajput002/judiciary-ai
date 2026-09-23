from typing import Annotated
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api import chat, documents, sessions

settings = get_settings()
setup_logging(debug=settings.debug)

app = FastAPI(
    title="LexiAI — Legal Research Agent",
    description="Domain-specific legal research AI with RAG, web search, and session memory.",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
