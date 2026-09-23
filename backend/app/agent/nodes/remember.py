"""Remember node — persists assistant message, citations, entities, and relationships."""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage, HumanMessage

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState, StageTrace
from app.agent.prompts.legal_domain import LEGAL_DOMAIN_SYSTEM
from app.db.models import Message, Citation, ResearchEntity, ResearchRelationship, Session
from app.llm.provider import get_chat_model
from app.core.logging import get_logger

logger = get_logger(__name__)

_ENTITY_SYSTEM = LEGAL_DOMAIN_SYSTEM + """
TASK — EXTRACT ENTITIES:
From the answer and query below, extract new legal entities discovered in this turn.

Output one entity per line:
ENTITY|<type>|<name>|<one-sentence summary>

Types: case, statute, issue, authority

Only extract entities that are clearly identifiable legal authorities, statutory provisions,
or legal issues — not generic legal concepts. Max 5 entities.
If none, output: NONE
"""


async def remember_node(state: AgentState, db: AsyncSession) -> AgentState:
    # --- 1. Persist assistant message ---
    pipeline_meta = {
        "routing_mode": state.routing_decision,
        "trace": [{"stage": t.stage, "summary": t.summary, "error": t.error} for t in state.pipeline_trace],
        "conflicts": len(state.conflicts),
    }

    msg = Message(
        session_id=state.session_id,
        role="assistant",
        content=state.draft_answer or "",
        routing_mode=state.routing_decision,
        pipeline_metadata=pipeline_meta,
    )
    db.add(msg)
    await db.flush()  # get msg.id

    # --- 2. Persist citations ---
    for cit in state.citations:
        row = Citation(
            message_id=msg.id,
            source_type=cit.source_type,
            document_id=cit.document_id,
            chunk_id=cit.chunk_id,
            title=cit.title,
            court_or_authority=cit.court_or_authority,
            url=cit.url,
            page_number=cit.page_number,
            section=cit.section,
            paragraph=cit.paragraph,
            case_name=cit.case_name,
            excerpt=cit.excerpt,
        )
        db.add(row)

    # --- 3. Fast regex extraction of legal entities (0ms latency, 0 tokens) ---
    try:
        import re
        entity_rows: list[ResearchEntity] = []
        existing_names = {e["name"].lower() for e in state.research_entities}

        full_text = f"{state.resolved_query or ''} {state.draft_answer or ''}"
        
        # Extract cases: e.g. "A. K. Gopalan v. State of Madras"
        case_matches = re.findall(r"([A-Z][A-Za-z\.\s]{2,30}(?:v\.|versus)\s+[A-Z][A-Za-z\.\s]{2,30})", full_text)
        for c in case_matches:
            clean_c = c.strip().rstrip(".,;:")
            if len(clean_c) >= 7 and clean_c.lower() not in existing_names:
                existing_names.add(clean_c.lower())
                row = ResearchEntity(
                    session_id=state.session_id,
                    entity_type="case",
                    name=clean_c,
                    summary=f"Case authority: {clean_c}",
                    source_message_id=msg.id,
                )
                db.add(row)
                entity_rows.append(row)
                if len(entity_rows) >= 4:
                    break

        # Extract articles/sections: e.g. "Article 21", "Section 42"
        statute_matches = re.findall(r"((?:Article|Section|Clause)\s+\d+[A-Za-z]?(?:\s+of\s+(?:the\s+)?[A-Z][A-Za-z\s]+(?:Act|Constitution))?)", full_text)
        for s in statute_matches:
            clean_s = s.strip().rstrip(".,;:")
            if clean_s.lower() not in existing_names:
                existing_names.add(clean_s.lower())
                row = ResearchEntity(
                    session_id=state.session_id,
                    entity_type="statute",
                    name=clean_s,
                    summary=f"Statutory authority: {clean_s}",
                    source_message_id=msg.id,
                )
                db.add(row)
                entity_rows.append(row)
                if len(entity_rows) >= 8:
                    break
    except Exception as exc:
        logger.warning("[Remember] Entity extraction failed: %s", exc)

    # --- 4. Bump session last_active_at ---
    session = await db.get(Session, state.session_id)
    if session:
        session.last_active_at = datetime.now(timezone.utc)

    await db.commit()

    state.pipeline_trace.append(StageTrace(stage="Remember", summary="Persisted message, citations, entities"))
    logger.info("[Remember] done for session %s", state.session_id)
    return state


async def remember_user_message(session_id: uuid.UUID, content: str, db: AsyncSession) -> Message:
    """Persist the user's message before the graph runs."""
    msg = Message(session_id=session_id, role="user", content=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
