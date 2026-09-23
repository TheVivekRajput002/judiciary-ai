"""Synthesize node — composes the structured legal research answer."""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState, StageTrace
from app.agent.prompts.legal_domain import LEGAL_DOMAIN_SYSTEM
from app.llm.provider import get_chat_model
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM = LEGAL_DOMAIN_SYSTEM + """
TASK — SYNTHESIZE:
Write a comprehensive, authoritative, and well-structured legal research answer for the user directly grounded in the provided EVIDENCE.

CRITICAL INSTRUCTIONS:
1. Ground your answer thoroughly in the provided DOCUMENT EXCERPTS and WEB SOURCES.
2. Quote and reference specific pages, sections, paragraphs, and statutes directly from the evidence where available.
3. If the user's question relates to an uploaded document, answer it directly using the facts, legal analysis, and holdings in the document excerpts.
4. WEB SOURCES & INTERNET CITATIONS:
   - When answering using information from WEB SEARCH SOURCES or internet search, you MUST explicitly mention the source name or domain in your text (e.g., "According to LiveLaw...", "As reported on Indian Kanoon...", "Per the Supreme Court official portal (sci.gov.in)...").
   - Embed clickable markdown links to the exact URLs from the provided web sources (e.g. `[LiveLaw Article](https://...)` or `[Indian Kanoon](https://...)`).
5. Structure the response clearly with relevant markdown headings (e.g. ## Summary, ## Legal Analysis & Key Holdings, ## Statutory / Judicial Context, ## Conclusion).
6. Do NOT fabricate or hallucinate URLs not present in the provided sources.
"""


async def synthesize_node(state: AgentState) -> AgentState:
    conflict_context = ""
    if state.conflicts:
        conflict_context = "\n\nCONFLICTS DETECTED:\n" + "\n".join(
            f"- {c.description}: '{c.position_a}' (sources: {c.sources_a}) vs '{c.position_b}' (sources: {c.sources_b})"
            for c in state.conflicts
        )

    # Format the actual retrieved evidence with full context and page numbers
    evidence_parts = []
    if state.retrieved_chunks:
        evidence_parts.append("=== UPLOADED DOCUMENT EXCERPTS ===")
        for i, c in enumerate(state.retrieved_chunks[:4]):
            pg = f"Page {c.page_number}" if c.page_number else "N/A"
            sec = f" | Section: {c.section}" if c.section else ""
            evidence_parts.append(f"Excerpt {i+1} [{c.document_filename}, {pg}{sec}]:\n{c.content[:1200]}")
    if state.retrieved_web_results:
        evidence_parts.append("=== WEB SEARCH SOURCES (INTERNET) ===")
        for i, w in enumerate(state.retrieved_web_results[:4]):
            evidence_parts.append(f"Web Source {i+1} [Title: {w.title} | Source: {w.domain} | URL: {w.url}]:\n{w.content[:800]}")

    evidence_text = "\n\n".join(evidence_parts) if evidence_parts else "No specific evidence retrieved."

    model = get_chat_model(temperature=0.1, max_tokens=1000)
    response = await model.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(
            content=(
                f"User Question: {state.raw_query}\n"
                f"Resolved Query: {state.resolved_query or state.raw_query}\n\n"
                f"AVAILABLE EVIDENCE:\n{evidence_text}\n\n"
                f"REASONING CONTEXT:\n{state.reasoning_notes or 'Analyze the evidence directly.'}\n"
                f"{conflict_context}"
            )
        ),
    ])

    state.draft_answer = response.content.strip()
    state.pipeline_trace.append(StageTrace(stage="Synthesize", summary="Draft answer composed"))
    logger.info("[Synthesize] draft_answer length=%d", len(state.draft_answer or ""))
    return state
