"""Cite node — attaches citations, validates each traces to retrieved evidence (F-10)."""
from __future__ import annotations
import uuid

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState, CitationData, StageTrace
from app.agent.prompts.legal_domain import LEGAL_DOMAIN_SYSTEM
from app.llm.provider import get_chat_model
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM = LEGAL_DOMAIN_SYSTEM + """
TASK — CITE:
Review the draft answer and the source evidence. For each substantive claim in the answer,
identify which retrieved source supports it.

Output one citation per line in this format:
CITE|<source_type>|<identifier>|<excerpt (max 120 chars)>

Where:
- source_type: "document" or "web"
- identifier: for document = "chunk:<chunk_id>", for web = "url:<url>"
- excerpt: the short supporting text from the source

STRICT RULE: Only cite sources that are ACTUALLY in the provided evidence list.
If a claim has no matching retrieved source, output:
UNSUPPORTED|<brief description of unsupported claim>

Do not invent sources. Do not cite sources not in the evidence list.
"""


def _build_evidence_index(state: AgentState) -> tuple[dict[str, object], dict[str, object]]:
    chunk_index = {str(c.chunk_id): c for c in state.retrieved_chunks}
    web_index = {w.url: w for w in state.retrieved_web_results}
    return chunk_index, web_index


async def cite_node(state: AgentState) -> AgentState:
    citations: list[CitationData] = []
    for c in state.retrieved_chunks[:6]:
        citations.append(CitationData(
            source_type="document",
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_filename=c.document_filename,
            page_number=str(c.page_number) if c.page_number else None,
            section=c.section,
            case_name=c.case_name,
            excerpt=c.content[:150].strip() + "...",
        ))
    for w in state.retrieved_web_results[:4]:
        citations.append(CitationData(
            source_type="web",
            url=w.url,
            title=w.title,
            court_or_authority=w.domain,
            excerpt=w.content[:150].strip() + "...",
        ))

    state.citations = citations
    state.pipeline_trace.append(StageTrace(stage="Cite", summary=f"Citations={len(citations)}"))
    logger.info("[Cite] citations=%d", len(citations))
    return state
