"""POST /api/chat — SSE streaming endpoint.

Streams stage events (drives PipelineProgressIndicator) then the final answer
in Vercel AI SDK Data Stream Protocol format.
"""
from __future__ import annotations
import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.db.models import Message
from app.agent.graph import build_graph
from app.agent.state import AgentState
from app.agent.nodes.remember import remember_user_message
from app.memory.context_loader import build_initial_state
from app.core.logging import get_logger
from app.core.errors import http_bad_request

router = APIRouter()
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str


def _sse(event: str, data: dict | str) -> str:
    """Format a single SSE message."""
    payload = json.dumps(data) if isinstance(data, dict) else data
    return f"event: {event}\ndata: {payload}\n\n"


def _text_token(token: str) -> str:
    """Vercel AI SDK Data Stream Protocol — plain text token."""
    return f"0:{json.dumps(token)}\n"


async def _stream_pipeline(
    session_id: uuid.UUID,
    message: str,
) -> AsyncGenerator[str, None]:
    """Run the full agent pipeline and yield SSE events."""
    # Use a dedicated DB session for this long-running request
    async with AsyncSessionLocal() as db:
        try:
            # 1. Persist user message
            await remember_user_message(session_id, message, db)

            # 2. Build initial state from session context
            yield _sse("stage", {"stage": "Understand", "status": "running"})
            state = await build_initial_state(session_id, message, db)

            # 3. Build and run the graph
            graph = build_graph(db)

            final_state_data = None
            async for event in graph.astream(state, stream_mode="values"):
                final_state_data = event

                # Emit stage events as nodes complete
                pipeline_trace = event.get("pipeline_trace") if isinstance(event, dict) else getattr(event, "pipeline_trace", [])
                if pipeline_trace:
                    latest = pipeline_trace[-1]
                    stage_name = getattr(latest, "stage", None) or (latest.get("stage") if isinstance(latest, dict) else "")
                    stage_error = getattr(latest, "error", None) or (latest.get("error") if isinstance(latest, dict) else None)
                    stage_summary = getattr(latest, "summary", None) or (latest.get("summary") if isinstance(latest, dict) else "")
                    yield _sse("stage", {
                        "stage": stage_name,
                        "status": "done" if not stage_error else "error",
                        "summary": stage_summary,
                    })

            # Extract fields from final state (dict or dataclass)
            if isinstance(final_state_data, dict):
                answer = final_state_data.get("draft_answer") or ""
                raw_citations = final_state_data.get("citations") or []
                raw_conflicts = final_state_data.get("conflicts") or []
                error_msg = final_state_data.get("error")
                routing_mode = final_state_data.get("routing_decision")
            elif final_state_data is not None:
                answer = final_state_data.draft_answer or ""
                raw_citations = final_state_data.citations or []
                raw_conflicts = final_state_data.conflicts or []
                error_msg = final_state_data.error
                routing_mode = final_state_data.routing_decision
            else:
                answer = ""
                raw_citations = []
                raw_conflicts = []
                error_msg = None
                routing_mode = None

            # 4. Stream the final answer as tokens
            chunk_size = 20
            for i in range(0, len(answer), chunk_size):
                yield _text_token(answer[i:i + chunk_size])
                await asyncio.sleep(0)  # yield control

            # 5. Send citations and conflict metadata
            citations_payload = []
            for c in raw_citations:
                if isinstance(c, dict):
                    citations_payload.append({
                        "source_type": c.get("source_type"),
                        "document_filename": c.get("document_filename"),
                        "page_number": c.get("page_number"),
                        "section": c.get("section"),
                        "case_name": c.get("case_name"),
                        "url": c.get("url"),
                        "title": c.get("title"),
                        "court_or_authority": c.get("court_or_authority"),
                        "excerpt": c.get("excerpt"),
                    })
                else:
                    citations_payload.append({
                        "source_type": getattr(c, "source_type", None),
                        "document_filename": getattr(c, "document_filename", None),
                        "page_number": getattr(c, "page_number", None),
                        "section": getattr(c, "section", None),
                        "case_name": getattr(c, "case_name", None),
                        "url": getattr(c, "url", None),
                        "title": getattr(c, "title", None),
                        "court_or_authority": getattr(c, "court_or_authority", None),
                        "excerpt": getattr(c, "excerpt", None),
                    })

            conflicts_payload = []
            for c in raw_conflicts:
                if isinstance(c, dict):
                    conflicts_payload.append({
                        "position_a": c.get("position_a"),
                        "sources_a": c.get("sources_a"),
                        "position_b": c.get("position_b"),
                        "sources_b": c.get("sources_b"),
                        "description": c.get("description"),
                    })
                else:
                    conflicts_payload.append({
                        "position_a": getattr(c, "position_a", None),
                        "sources_a": getattr(c, "sources_a", None),
                        "position_b": getattr(c, "position_b", None),
                        "sources_b": getattr(c, "sources_b", None),
                        "description": getattr(c, "description", None),
                    })

            yield _sse("citations", citations_payload)
            if conflicts_payload:
                yield _sse("conflicts", conflicts_payload)

            # 6. Error event if any pipeline errors occurred
            if error_msg:
                yield _sse("error", {"message": error_msg})

            # 7. Done
            yield _sse("done", {"routing_mode": routing_mode})

        except Exception as exc:
            logger.exception("Pipeline error for session %s: %s", session_id, exc)
            yield _sse("error", {"message": f"Pipeline error: {str(exc)}"})


@router.post("/chat")
async def chat(body: ChatRequest):
    if not body.message.strip():
        raise http_bad_request("Message cannot be empty")

    return StreamingResponse(
        _stream_pipeline(body.session_id, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
