"""Plan node — decides routing (document/web/combined) and drafts a retrieval plan."""
from __future__ import annotations
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState, StageTrace
from app.agent.prompts.legal_domain import LEGAL_DOMAIN_SYSTEM
from app.llm.provider import get_chat_model
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM = LEGAL_DOMAIN_SYSTEM + """
TASK — PLAN:
You are the planning stage. Decide the research strategy for the given query.

Available documents in this session: {docs}
Conversation context:
{conversation_context}

You must output EXACTLY this format (no extra text):
ROUTING: <document|web|combined>
RETRIEVAL_PLAN: <1-2 sentences describing specifically what information to look for and where>

ROUTING RULES:
- document: Only when the query is specifically about content inside the uploaded document(s) AND the user is not asking to search the web.
- combined: When the query asks about both the document AND wider law, or when the document may have partial info.
- web: When NO documents are uploaded, OR when the user explicitly asks to search the internet/web, OR when the previous turn already said the document doesn't contain the answer (i.e. the prior assistant reply mentioned the topic wasn't found in the document). In conversation follow-ups like 'search from the internet' or 'look it up online', ALWAYS use 'web'.

IMPORTANT: If the conversation history shows the assistant just said something was not found in the uploaded document, you MUST use 'web' routing for the follow-up request.
"""


_WEB_INTENT_PATTERNS = [
    "search", "internet", "online", "web", "look up", "look it up",
    "find online", "google", "search online", "search the web",
    "find from internet", "search from internet", "check online",
]


def _detect_web_intent(query: str, recent_messages: list[dict]) -> bool:
    """Return True if the user explicitly wants a web/internet search."""
    q_lower = query.lower()
    for pat in _WEB_INTENT_PATTERNS:
        if pat in q_lower:
            return True
    # If last assistant message said 'not found in document', next query is implicitly web
    for m in reversed(recent_messages[-4:]):
        if m.get("role") == "assistant":
            content = m.get("content", "").lower()
            if any(phrase in content for phrase in [
                "not found in the document", "not in the document",
                "document does not contain", "not mentioned in the document",
                "insufficient evidence", "uploaded document",
                "couldn't find", "could not find",
                "no information in the document",
            ]):
                return True
            break
    return False


async def plan_node(state: AgentState) -> AgentState:
    logger.info("[Plan] resolved_query=%s", (state.resolved_query or "")[:100])

    has_docs = bool(state.session_documents)
    doc_list = ", ".join(d["filename"] for d in state.session_documents) if has_docs else "none"

    # Build short conversation context for the model
    conv_lines = []
    for m in state.recent_messages[-6:]:
        role = m.get("role", "user").upper()
        snippet = m.get("content", "")[:200]
        conv_lines.append(f"{role}: {snippet}")
    conversation_context = "\n".join(conv_lines) if conv_lines else "None"

    system = _SYSTEM.format(docs=doc_list, conversation_context=conversation_context)

    # Fast-path: detect explicit web intent before calling LLM
    explicit_web = _detect_web_intent(state.resolved_query or state.raw_query, state.recent_messages)

    if explicit_web:
        routing: Literal["document", "web", "combined"] = "web"
        plan = f"Search the internet for information relevant to: {state.resolved_query or state.raw_query}"
        logger.info("[Plan] explicit web intent detected — routing=web")
    else:
        model = get_chat_model(temperature=0.1, max_tokens=150)
        response = await model.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Query: {state.resolved_query}"),
        ])
        text = response.content.strip()

        routing = "combined" if has_docs else "web"
        plan = ""

        for line in text.splitlines():
            if line.startswith("ROUTING:"):
                val = line.replace("ROUTING:", "").strip().lower()
                if val in ("document", "web", "combined"):
                    routing = val  # type: ignore[assignment]
            elif line.startswith("RETRIEVAL_PLAN:"):
                plan = line.replace("RETRIEVAL_PLAN:", "").strip()

        if not plan:
            plan = f"Retrieve information relevant to: {state.resolved_query}"

    state.routing_decision = routing
    state.retrieval_plan = plan
    state.pipeline_trace.append(StageTrace(stage="Plan", summary=f"Routing={routing}: {plan[:80]}"))
    logger.info("[Plan] routing=%s plan=%s", routing, plan[:80])
    return state
