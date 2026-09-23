"""Document ingestion pipeline: extract → chunk → embed → store.

Called from the documents API as a FastAPI BackgroundTask.
Raw files are discarded after text extraction (storage_path stays null).
"""
from __future__ import annotations
import asyncio
import io
import uuid
from datetime import datetime, timezone

import docx
import pypdf
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Document, DocumentChunk
from app.db.session import AsyncSessionLocal
from app.llm.embeddings import embed_texts
from app.rag.chunking import chunk_document

logger = get_logger(__name__)


def _extract_pdf(data: bytes) -> list[tuple[str, int]]:
    """Return list of (page_text, page_number) from PDF bytes."""
    reader = pypdf.PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((text, i + 1))
    return pages


def _extract_docx(data: bytes) -> list[tuple[str, int]]:
    """Return paragraphs grouped into pseudo-pages of ~500 lines each."""
    doc = docx.Document(io.BytesIO(data))
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    # Group into chunks of 50 paragraphs as proxy "pages"
    page_size = 50
    pages = []
    for i in range(0, len(lines), page_size):
        page_text = "\n".join(lines[i : i + page_size])
        pages.append((page_text, (i // page_size) + 1))
    return pages


def _extract_txt(data: bytes) -> list[tuple[str, int]]:
    text = data.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    page_size = 60
    pages = []
    for i in range(0, len(lines), page_size):
        page_text = "\n".join(lines[i : i + page_size])
        pages.append((page_text, (i // page_size) + 1))
    return pages


async def run_ingestion(
    document_id: uuid.UUID,
    file_data: bytes,
    file_type: str,
) -> None:
    """Background ingestion task. Updates document status in-place."""
    async with AsyncSessionLocal() as db:
        try:
            # Mark as processing
            doc = await db.get(Document, document_id)
            if doc is None:
                logger.error("Ingestion: document %s not found", document_id)
                return
            doc.status = "processing"
            doc.error_message = None
            await db.commit()

            # Extract text
            if file_type == "pdf":
                pages = _extract_pdf(file_data)
            elif file_type in ("docx", "doc"):
                pages = _extract_docx(file_data)
            else:
                pages = _extract_txt(file_data)

            if not pages:
                doc.status = "failed"
                doc.error_message = "No extractable text found in document (may be empty or scanned image without OCR)."
                await db.commit()
                return

            doc.page_count = len(pages)

            # Chunk
            raw_chunks = chunk_document(pages)
            logger.info("Ingestion: %d chunks from document %s", len(raw_chunks), document_id)

            if not raw_chunks:
                doc.status = "processed"
                doc.processed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Embed in batches
            texts = [c.content for c in raw_chunks]
            all_embeddings: list[list[float]] = []
            settings = get_settings()
            batch_size = 8 if settings.embedding_provider == "voyage" else 128
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = await embed_texts(batch)
                all_embeddings.extend(embeddings)
                if settings.embedding_provider == "voyage" and i + batch_size < len(texts):
                    # Rate-limit safety pause between batches for Voyage AI
                    await asyncio.sleep(1.5)

            # Store chunks
            chunk_rows = [
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    embedding=all_embeddings[i],
                    page_number=c.page_number,
                    section=c.section,
                    paragraph=c.paragraph,
                    token_count=len(c.content) // 4,
                )
                for i, c in enumerate(raw_chunks)
            ]
            db.add_all(chunk_rows)

            doc.status = "processed"
            doc.processed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Ingestion complete: document %s", document_id)

        except Exception as exc:
            logger.exception("Ingestion failed for document %s: %s", document_id, exc)
            try:
                doc = await db.get(Document, document_id)
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(exc)
                    await db.commit()
            except Exception:
                pass
