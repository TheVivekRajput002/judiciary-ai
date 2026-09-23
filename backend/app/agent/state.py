"""AgentState — the single shared state object passed between all LangGraph nodes."""
from __future__ import annotations
import uuid
from typing import Optional, Literal, Any
from dataclasses import dataclass, field

from app.rag.retrieval import ChunkResult
from app.web_search.tool import WebResult


@dataclass
class ConflictBlock:
    """Represents a disagreement detected between two or more sources."""
    position_a: str
    sources_a: list[str]
    position_b: str
    sources_b: list[str]
    description: str


@dataclass
class CitationData:
    """Citation attached to a substantive claim in the draft answer."""
    source_type: Literal["document", "web"]
    # Document citation fields
    chunk_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    document_filename: Optional[str] = None
    page_number: Optional[str] = None
    section: Optional[str] = None
    paragraph: Optional[str] = None
    case_name: Optional[str] = None
    excerpt: Optional[str] = None
    # Web citation fields
    url: Optional[str] = None
    title: Optional[str] = None
    court_or_authority: Optional[str] = None
    citation_date: Optional[str] = None


@dataclass
class StageTrace:
    stage: str
    summary: str
    error: Optional[str] = None


@dataclass
class AgentState:
    # ── Inputs (set by API layer) ─────────────────────────────────────────
    session_id: uuid.UUID = field(default_factory=uuid.uuid4)
    raw_query: str = ""

    # ── Understand node ──────────────────────────────────────────────────
    resolved_query: Optional[str] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None

    # ── Plan node ────────────────────────────────────────────────────────
    routing_decision: Optional[Literal["document", "web", "combined"]] = None
    retrieval_plan: Optional[str] = None  # short description of what to look for

    # ── Retrieve node ────────────────────────────────────────────────────
    retrieved_chunks: list[ChunkResult] = field(default_factory=list)
    retrieved_web_results: list[WebResult] = field(default_factory=list)

    # ── Research node ────────────────────────────────────────────────────
    evidence_sufficient: bool = True  # set False → short-circuit to InsufficientEvidence

    # ── Reason node ─────────────────────────────────────────────────────
    reasoning_notes: Optional[str] = None  # internal — never shown to user directly
    conflicts: list[ConflictBlock] = field(default_factory=list)

    # ── Synthesize node ──────────────────────────────────────────────────
    draft_answer: Optional[str] = None

    # ── Cite node ────────────────────────────────────────────────────────
    citations: list[CitationData] = field(default_factory=list)

    # ── Pipeline tracing (every node appends) ────────────────────────────
    pipeline_trace: list[StageTrace] = field(default_factory=list)

    # ── Error (any node can set) ─────────────────────────────────────────
    error: Optional[str] = None

    # ── Session context (loaded by context_loader before graph runs) ─────
    session_documents: list[dict] = field(default_factory=list)   # [{id, filename, status}]
    recent_messages: list[dict] = field(default_factory=list)     # [{role, content}]
    research_entities: list[dict] = field(default_factory=list)   # [{type, name, summary, metadata}]
    research_relationships: list[dict] = field(default_factory=list)
