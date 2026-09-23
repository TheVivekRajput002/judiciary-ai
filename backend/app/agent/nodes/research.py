"""Research node — evaluates relevance and reliability of retrieved evidence."""
from __future__ import annotations

from app.agent.state import AgentState, StageTrace
from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum chunks/results to consider evidence sufficient
MIN_CHUNK_SIMILARITY = 0.35
MIN_EVIDENCE_ITEMS = 1


async def research_node(state: AgentState) -> AgentState:
    chunks = state.retrieved_chunks
    web = state.retrieved_web_results

    # Filter low-similarity chunks
    good_chunks = [c for c in chunks if c.similarity >= MIN_CHUNK_SIMILARITY]

    total_evidence = len(good_chunks) + len(web)

    if total_evidence < MIN_EVIDENCE_ITEMS:
        state.evidence_sufficient = False
        state.pipeline_trace.append(
            StageTrace(stage="Research", summary="Insufficient evidence found — short-circuiting")
        )
        logger.info("[Research] evidence_sufficient=False (chunks=%d, web=%d)", len(good_chunks), len(web))
        return state

    # Replace chunks with the filtered set
    state.retrieved_chunks = good_chunks
    state.evidence_sufficient = True
    state.pipeline_trace.append(
        StageTrace(stage="Research", summary=f"Evidence OK: {len(good_chunks)} chunks, {len(web)} web results")
    )
    logger.info("[Research] evidence_sufficient=True (chunks=%d, web=%d)", len(good_chunks), len(web))
    return state
