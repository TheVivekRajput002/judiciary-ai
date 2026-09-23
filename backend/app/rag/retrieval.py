"""Semantic retrieval from document_chunks using pgvector."""
from __future__ import annotations
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.llm.embeddings import embed_query
from app.core.logging import get_logger

logger = get_logger(__name__)

TOP_N = 8
SIMILARITY_THRESHOLD = 0.35  # cosine distance; below this = not relevant enough


@dataclass
class ChunkResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    case_name: str | None
    content: str
    page_number: int | None
    section: str | None
    paragraph: str | None
    similarity: float


async def retrieve_chunks(
    query: str | list[str],
    session_id: uuid.UUID,
    db: AsyncSession,
    top_n: int = TOP_N,
) -> list[ChunkResult]:
    """Embed query string(s) and return top-N most similar chunks within this session.

    Accepts a single query or list of query variations (e.g. raw query + resolved query).
    Scoped to documents that belong to the given session and have status='processed'.
    """
    queries = [query] if isinstance(query, str) else query
    queries = [q.strip() for q in queries if q and q.strip()]

    if not queries:
        return []

    combined_chunks: dict[uuid.UUID, ChunkResult] = {}

    sql = text("""
        SELECT
            dc.id            AS chunk_id,
            dc.document_id,
            d.original_filename,
            d.case_name,
            dc.content,
            dc.page_number,
            dc.section,
            dc.paragraph,
            1 - (dc.embedding <=> :embedding ::vector) AS similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.session_id = :session_id
          AND d.status = 'processed'
          AND 1 - (dc.embedding <=> :embedding ::vector) > :threshold
        ORDER BY dc.embedding <=> :embedding ::vector
        LIMIT :top_n
    """)

    for q in queries:
        try:
            query_embedding = await embed_query(q)
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            result = await db.execute(
                sql,
                {
                    "embedding": embedding_str,
                    "session_id": str(session_id),
                    "threshold": SIMILARITY_THRESHOLD,
                    "top_n": top_n,
                },
            )
            rows = result.mappings().all()
            for row in rows:
                cid = row["chunk_id"]
                sim = float(row["similarity"])
                if cid not in combined_chunks or sim > combined_chunks[cid].similarity:
                    combined_chunks[cid] = ChunkResult(
                        chunk_id=cid,
                        document_id=row["document_id"],
                        document_filename=row["original_filename"],
                        case_name=row["case_name"],
                        content=row["content"],
                        page_number=row["page_number"],
                        section=row["section"],
                        paragraph=row["paragraph"],
                        similarity=sim,
                    )
        except Exception as exc:
            logger.warning("Error embedding query '%s': %s", q[:50], exc)

    # Sort all deduplicated chunks by highest similarity
    sorted_chunks = sorted(combined_chunks.values(), key=lambda c: c.similarity, reverse=True)
    logger.debug("Retrieval: %d total deduplicated chunks for %d queries", len(sorted_chunks), len(queries))
    return sorted_chunks[:top_n]
