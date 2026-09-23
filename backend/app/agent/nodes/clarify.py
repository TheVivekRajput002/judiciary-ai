"""Clarify node — short-circuit that returns a clarifying question as the assistant turn."""
from app.agent.state import AgentState, StageTrace
from app.core.logging import get_logger

logger = get_logger(__name__)


async def clarify_node(state: AgentState) -> AgentState:
    state.draft_answer = state.clarification_question or "Could you please clarify your question?"
    state.citations = []
    state.pipeline_trace.append(StageTrace(stage="Clarify", summary="Clarification question returned"))
    logger.info("[Clarify] question=%s", state.draft_answer[:80])
    return state
