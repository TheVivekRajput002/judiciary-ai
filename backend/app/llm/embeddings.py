"""Embedding factory supporting local FastEmbed (1024-dim) and Voyage AI."""
from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_fastembed_model = None
_voyage_client = None


def get_fastembed_model():
    global _fastembed_model
    if _fastembed_model is None:
        import os
        from fastembed import TextEmbedding
        threads = os.cpu_count() or 4
        logger.info("Initializing FastEmbed model (BAAI/bge-small-en-v1.5, 384-dim) with %d threads...", threads)
        _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=threads)
    return _fastembed_model


def get_async_voyage_client():
    global _voyage_client
    if _voyage_client is None:
        import voyageai
        settings = get_settings()
        _voyage_client = voyageai.AsyncClient(api_key=settings.voyage_api_key)
    return _voyage_client


async def _embed_texts_fastembed(texts: list[str]) -> list[list[float]]:
    model = get_fastembed_model()
    embeddings = await asyncio.to_thread(
        lambda: [e.tolist() for e in model.embed(texts, batch_size=128)]
    )
    return embeddings


async def _embed_query_fastembed(text: str) -> list[float]:
    model = get_fastembed_model()
    embeddings = await asyncio.to_thread(
        lambda: [e.tolist() for e in model.query_embed([text])]
    )
    return embeddings[0]


async def _embed_texts_voyage(texts: list[str]) -> list[list[float]]:
    from voyageai.error import RateLimitError, VoyageError

    @retry(
        retry=retry_if_exception_type((RateLimitError, VoyageError)),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _call():
        client = get_async_voyage_client()
        result = await client.embed(texts, model="voyage-3", input_type="document")
        return result.embeddings

    return await _call()


async def _embed_query_voyage(text: str) -> list[float]:
    from voyageai.error import RateLimitError, VoyageError

    @retry(
        retry=retry_if_exception_type((RateLimitError, VoyageError)),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _call():
        client = get_async_voyage_client()
        result = await client.embed([text], model="voyage-3", input_type="query")
        return result.embeddings[0]

    return await _call()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns list of 1024-dim vectors."""
    settings = get_settings()
    if settings.embedding_provider == "voyage" and settings.voyage_api_key:
        return await _embed_texts_voyage(texts)
    return await _embed_texts_fastembed(texts)


async def embed_query(text: str) -> list[float]:
    """Embed a single query string for asymmetric retrieval. Returns 1024-dim vector."""
    settings = get_settings()
    if settings.embedding_provider == "voyage" and settings.voyage_api_key:
        return await _embed_query_voyage(text)
    return await _embed_query_fastembed(text)
