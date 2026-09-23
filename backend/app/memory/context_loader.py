"""Loads session context from Postgres into the initial AgentState."""
from __future__ import annotations
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Message, Document, ResearchEntity, ResearchRelationship
from app.agent.state import AgentState
from app.core.logging import get_logger

logger = get_logger(__name__)

RECENT_MESSAGE_LIMIT = 10


async def build_initial_state(
    session_id: uuid.UUID,
    raw_query: str,
    db: AsyncSession,
) -> AgentState:
    """Build an AgentState pre-populated with session history and entities."""
    state = AgentState(session_id=session_id, raw_query=raw_query)

    # Recent messages (last N turns)
    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(RECENT_MESSAGE_LIMIT)
    )
    messages = list(reversed(msg_result.scalars().all()))
    state.recent_messages = [
        {"role": m.role, "content": m.content} for m in messages
    ]

    # Session documents (metadata only — not the text)
    doc_result = await db.execute(
        select(Document).where(Document.session_id == session_id)
    )
    docs = doc_result.scalars().all()
    state.session_documents = [
        {"id": str(d.id), "filename": d.original_filename, "status": d.status}
        for d in docs
    ]

    # Research entities (all discovered in this session)
    ent_result = await db.execute(
        select(ResearchEntity).where(ResearchEntity.session_id == session_id)
    )
    entities = ent_result.scalars().all()
    state.research_entities = [
        {
            "id": str(e.id),
            "entity_type": e.entity_type,
            "name": e.name,
            "summary": e.summary,
            "metadata": e.metadata_,
        }
        for e in entities
    ]

    # Research relationships
    rel_result = await db.execute(
        select(ResearchRelationship).where(ResearchRelationship.session_id == session_id)
    )
    rels = rel_result.scalars().all()
    state.research_relationships = [
        {
            "from_entity_id": str(r.from_entity_id),
            "to_entity_id": str(r.to_entity_id) if r.to_entity_id else None,
            "relationship_type": r.relationship_type,
            "description": r.description,
        }
        for r in rels
    ]

    logger.info(
        "[ContextLoader] session=%s messages=%d docs=%d entities=%d",
        session_id, len(messages), len(docs), len(entities),
    )
    return state
