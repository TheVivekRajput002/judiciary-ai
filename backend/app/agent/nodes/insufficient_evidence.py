"""InsufficientEvidence node — when RAG finds nothing, auto-fallback to web search.

If the original routing was 'document' or 'combined' and RAG returned no good chunks,
this node upgrades routing to 'web' and re-runs the web search so the user still gets
an answer from the internet rather than a dead-end message.
"""
from __future__ import annotations

from app.agent.state import AgentState, StageTrace
from app.web_search.tool import legal_search
from app.core.logging import get_logger

logger = get_logger(__name__)


async def insufficient_evidence_node(state: AgentState) -> AgentState:
    routing = state.routing_decision or "document"
    query = state.resolved_query or state.raw_query

    # If we were searching docs (or combined) and found nothing — auto-fallback to web
    if routing in ("document", "combined"):
        logger.info(
            "[InsufficientEvidence] doc/combined routing returned no evidence — "
            "auto-falling back to web search for query: %s", query[:100]
        )
        try:
            web_results = await legal_search(resolved_query=query)
            if web_results:
                # Promote routing to web and hand off evidence for normal reasoning/synthesis
                state.retrieved_web_results = web_results
                state.routing_decision = "web"
                state.evidence_sufficient = True  # allow normal pipeline to continue
                state.pipeline_trace.append(
                    StageTrace(
                        stage="InsufficientEvidence",
                        summary=f"Doc had no results — auto-fallback to web: {len(web_results)} results found",
                    )
                )
                logger.info("[InsufficientEvidence] web fallback found %d results", len(web_results))
                return state
        except Exception as exc:
            logger.warning("[InsufficientEvidence] web fallback search failed: %s", exc)

    # If web search also found nothing (or routing was already web), give a helpful message
    state.draft_answer = (
        f"**No Relevant Sources Found**\n\n"
        f"I searched both the uploaded documents and authoritative Indian legal websites, "
        f"but couldn't find adequate information to answer:\n\n> {query}\n\n"
        f"**Try:**\n"
        f"- Rephrasing with specific statute names, section numbers, or case citations\n"
        f"- Uploading a relevant judgment, gazette notification, or Act for document-based research\n"
        f"- Narrowing the date range or jurisdiction for recent judgments"
    )
    state.citations = []
    state.pipeline_trace.append(
        StageTrace(stage="InsufficientEvidence", summary="No usable evidence found even after web fallback")
    )
    logger.info("[InsufficientEvidence] fired (no fallback results) for query=%s", query[:80])
    return state
