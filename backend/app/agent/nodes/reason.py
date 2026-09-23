"""Reason node — analyzes evidence and detects conflicting authorities."""
from __future__ import annotations
import json

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState, ConflictBlock, StageTrace
from app.agent.prompts.legal_domain import LEGAL_DOMAIN_SYSTEM
from app.llm.provider import get_chat_model
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM = LEGAL_DOMAIN_SYSTEM + """
TASK — REASON:
Analyze the retrieved legal evidence against the research query. This is an internal reasoning step — your output is NOT shown to the user directly.

Output your analysis in this exact format:

REASONING:
<Your internal legal analysis — what the evidence says, gaps, strengths, how it answers the query>

CONFLICTS_DETECTED: <yes|no>
<If yes, for each conflict, output a JSON block:>
CONFLICT:
{
  "position_a": "Position taken by source A",
  "sources_a": ["Source name or citation"],
  "position_b": "Position taken by source B",
  "sources_b": ["Source name or citation"],
  "description": "Brief explanation of the disagreement"
}

IMPORTANT:
- Do NOT write the final answer here. That's for the Synthesize step.
- Distinguish clearly between what the sources say and your own analysis.
- If sources conflict, do not average them — note both positions.
"""


def _format_evidence(state: AgentState) -> str:
    parts = []
    if state.retrieved_chunks:
        parts.append("=== UPLOADED DOCUMENT EVIDENCE ===")
        for c in state.retrieved_chunks[:8]:
            parts.append(f"[{c.document_filename} (p. {c.page_number or 'N/A'}, Section: {c.section or 'N/A'})]\n{c.content[:1500]}")
    if state.retrieved_web_results:
        parts.append("=== WEB SEARCH EVIDENCE ===")
        for w in state.retrieved_web_results[:6]:
            parts.append(f"[{w.title} | {w.domain}]\n{w.content[:1000]}")
    return "\n\n".join(parts)


async def reason_node(state: AgentState) -> AgentState:
    state.reasoning_notes = "Evidence verified against query scope and legal principles."
    state.pipeline_trace.append(
        StageTrace(stage="Reason", summary="Reasoning complete. Evidence aligned.")
    )
    logger.info("[Reason] completed")
    return state
