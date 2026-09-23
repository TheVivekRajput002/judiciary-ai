"""LangGraph StateGraph — the full Understand→Plan→Retrieve→Research→Reason→Synthesize→Cite→Remember pipeline."""
from __future__ import annotations
from typing import Literal

from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.agent.nodes import (
    understand,
    plan,
    retrieve,
    research,
    reason,
    synthesize,
    cite,
    remember,
    clarify,
    insufficient_evidence,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------

def route_after_understand(state: AgentState) -> Literal["clarify", "plan"]:
    if state.clarification_needed:
        return "clarify"
    return "plan"


def route_after_research(state: AgentState) -> Literal["insufficient_evidence", "reason"]:
    if not state.evidence_sufficient:
        return "insufficient_evidence"
    return "reason"


def route_after_insufficient_evidence(state: AgentState) -> Literal["reason", "remember"]:
    """If web fallback in insufficient_evidence succeeded, continue to reason/synthesize."""
    if state.evidence_sufficient:
        return "reason"
    return "remember"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(db: AsyncSession) -> StateGraph:
    """Build and compile the LangGraph agent graph.

    The db session is injected here so nodes that need DB access (retrieve,
    remember) receive it via closure — keeping node signatures clean.
    """

    graph = StateGraph(AgentState)

    # Wrap DB-dependent nodes with the session
    async def _retrieve(state: AgentState) -> AgentState:
        return await retrieve.retrieve_node(state, db)

    async def _remember(state: AgentState) -> AgentState:
        return await remember.remember_node(state, db)

    # Register nodes
    graph.add_node("understand", understand.understand_node)
    graph.add_node("plan", plan.plan_node)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("research", research.research_node)
    graph.add_node("reason", reason.reason_node)
    graph.add_node("synthesize", synthesize.synthesize_node)
    graph.add_node("cite", cite.cite_node)
    graph.add_node("remember", _remember)
    graph.add_node("clarify", clarify.clarify_node)
    graph.add_node("insufficient_evidence", insufficient_evidence.insufficient_evidence_node)

    # Edges
    graph.set_entry_point("understand")

    graph.add_conditional_edges("understand", route_after_understand, {
        "clarify": "clarify",
        "plan": "plan",
    })

    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "research")

    graph.add_conditional_edges("research", route_after_research, {
        "insufficient_evidence": "insufficient_evidence",
        "reason": "reason",
    })

    # After insufficient_evidence: if web fallback succeeded → reason; else → remember (dead end)
    graph.add_conditional_edges("insufficient_evidence", route_after_insufficient_evidence, {
        "reason": "reason",
        "remember": "remember",
    })

    graph.add_edge("reason", "synthesize")
    graph.add_edge("synthesize", "cite")
    graph.add_edge("cite", "remember")

    # clarify short-circuit feeds into remember so every turn is persisted
    graph.add_edge("clarify", "remember")

    graph.add_edge("remember", END)

    return graph.compile()

