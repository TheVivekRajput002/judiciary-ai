"""Retrieve node — calls RAG and/or web search based on routing decision."""
from __future__ import annotations
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState, StageTrace
from app.rag.retrieval import retrieve_chunks
from app.web_search.tool import legal_search
from app.core.logging import get_logger

logger = get_logger(__name__)


async def retrieve_node(state: AgentState, db: AsyncSession) -> AgentState:
    has_docs = bool(state.session_documents)
    routing = state.routing_decision or ("combined" if has_docs else "web")
    query = state.retrieval_plan or state.resolved_query or state.raw_query

    # For follow-up searches, seed with session entity names (F-06)
    context_entities = [e["name"] for e in state.research_entities] if state.research_entities else None

    chunks = []
    web_results = []

    # If documents exist in this session, ALWAYS perform RAG retrieval with both raw and resolved queries
    if has_docs or routing in ("document", "combined"):
        try:
            rag_queries = []
            if state.raw_query and state.raw_query.strip():
                rag_queries.append(state.raw_query.strip())
            if state.resolved_query and state.resolved_query.strip() and state.resolved_query != state.raw_query:
                rag_queries.append(state.resolved_query.strip())
            if state.retrieval_plan and state.retrieval_plan.strip() and state.retrieval_plan not in rag_queries:
                rag_queries.append(state.retrieval_plan.strip())

            chunks = await retrieve_chunks(
                query=rag_queries or query,
                session_id=state.session_id,
                db=db,
            )
            logger.info("[Retrieve] %d chunks retrieved", len(chunks))
        except Exception as exc:
            logger.warning("[Retrieve] RAG failed: %s", exc)
            state.error = f"Document retrieval error: {exc}"

    # Perform web search if routing specifies web/combined or as fallback if no doc chunks found
    if routing in ("web", "combined") or (has_docs and not chunks):
        try:
            web_results = await legal_search(
                resolved_query=query,
                context_entities=context_entities,
            )
            logger.info("[Retrieve] %d web results retrieved", len(web_results))
        except Exception as exc:
            logger.warning("[Retrieve] Web search failed: %s", exc)
            if not state.error:
                state.error = f"Web search error: {exc}"

    state.retrieved_chunks = chunks
    state.retrieved_web_results = web_results
    state.pipeline_trace.append(
        StageTrace(
            stage="Retrieve",
            summary=f"chunks={len(chunks)}, web={len(web_results)}, routing={routing}",
        )
    )
    return state
