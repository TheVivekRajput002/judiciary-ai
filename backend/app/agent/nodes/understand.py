"""Understand node — resolves references, detects out-of-domain, flags ambiguity."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState, StageTrace
from app.agent.prompts.legal_domain import LEGAL_DOMAIN_SYSTEM
from app.llm.provider import get_chat_model
from app.memory.reference_resolver import resolve_references
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM = LEGAL_DOMAIN_SYSTEM + """
TASK — UNDERSTAND:
You are the first stage. Given the raw user query and session context, you must:

1. DOMAIN CHECK: If the query is completely unrelated to law (e.g. cooking, sports, weather), respond with:
   DECISION: OUT_OF_DOMAIN

2. AMBIGUITY CHECK: ONLY flag as ambiguous if the query is COMPLETELY unintelligible and context provides NO clue.
   DO NOT flag as ambiguous if:
   - The user is giving a follow-up instruction referencing the previous conversation (e.g. 'search from the internet', 'look it up', 'try online', 'what about the second one')
   - The conversation history makes the intent clear
   If genuinely ambiguous with no context at all:
   DECISION: CLARIFY
   QUESTION: <one clear clarifying question>

3. RESOLVE: Otherwise (including ALL conversational follow-ups), rewrite the query resolving all pronouns
   and implicit references using the full conversation history. Return:
   DECISION: RESOLVED
   RESOLVED_QUERY: <the fully explicit, self-contained research query>

   For follow-up instructions like 'search from the internet' or 'look it up online', combine them with the
   topic from the PREVIOUS user message and recent assistant reply to produce a complete query like:
   'Search the internet for [topic from previous conversation]'

Be specific about Indian legal references (cite Act names, section numbers if mentioned).
Do NOT start researching or answering — only understand and resolve.
"""


async def understand_node(state: AgentState) -> AgentState:
    logger.info("[Understand] raw_query=%s", state.raw_query[:100])

    # First apply rule-based reference resolution
    resolved = resolve_references(state.raw_query, state.recent_messages, state.research_entities)

    model = get_chat_model(temperature=0.1, max_tokens=200)
    context_block = _build_context(state)

    response = await model.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"{context_block}\n\nRaw query: {state.raw_query}\nPre-resolved: {resolved}"),
    ])
    text = response.content.strip()

    if "DECISION: OUT_OF_DOMAIN" in text:
        state.clarification_needed = True
        state.clarification_question = (
            "I'm LexiAI, a legal research assistant specialising in Indian law. "
            "I can only help with legal research questions. Please ask me about statutes, "
            "judgments, legal provisions, or case law."
        )
        state.pipeline_trace.append(StageTrace(stage="Understand", summary="Out-of-domain query detected"))
        return state

    if "DECISION: CLARIFY" in text:
        lines = text.splitlines()
        question = next((l.replace("QUESTION:", "").strip() for l in lines if l.startswith("QUESTION:")), "Could you clarify your question?")
        state.clarification_needed = True
        state.clarification_question = question
        state.pipeline_trace.append(StageTrace(stage="Understand", summary="Ambiguous query — clarification requested"))
        return state

    # Extract resolved query
    for line in text.splitlines():
        if line.startswith("RESOLVED_QUERY:"):
            state.resolved_query = line.replace("RESOLVED_QUERY:", "").strip()
            break
    if not state.resolved_query:
        state.resolved_query = resolved  # fallback

    state.pipeline_trace.append(StageTrace(stage="Understand", summary=f"Resolved: {state.resolved_query[:80]}"))
    logger.info("[Understand] resolved=%s", state.resolved_query[:100])
    return state


def _build_context(state: AgentState) -> str:
    parts = []
    if state.session_documents:
        docs = ", ".join(d["filename"] for d in state.session_documents)
        parts.append(f"Uploaded session documents: {docs}")
    if state.recent_messages:
        # Include last 8 messages (4 full turns) for rich conversational context
        history = "\n".join(
            f"{m['role'].upper()}: {m['content'][:400]}"
            for m in state.recent_messages[-8:]
        )
        parts.append(f"Conversation history:\n{history}")
    if state.research_entities:
        entities = ", ".join(f"{e['entity_type']}:{e['name']}" for e in state.research_entities[:10])
        parts.append(f"Session entities (already discussed): {entities}")
    return "\n\n".join(parts) if parts else "No prior context."
