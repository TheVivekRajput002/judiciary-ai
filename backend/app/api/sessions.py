import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.session import get_db
from app.db.models import Session as DBSession, Message, ResearchEntity
from app.core.errors import http_not_found

router = APIRouter()


class SessionCreate(BaseModel):
    title: str | None = None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    routing_mode: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    last_active_at: datetime
    model_config = {"from_attributes": True}


class SessionDetail(SessionOut):
    messages: list[MessageOut] = []


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    session = DBSession(title=body.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DBSession).order_by(DBSession.last_active_at.desc()).limit(20)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await db.get(DBSession, session_id)
    if session is None:
        raise http_not_found("Session not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "last_active_at": session.last_active_at,
        "messages": messages,
    }


@router.delete("/sessions/{session_id}/messages", status_code=204)
async def clear_session_messages(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await db.get(DBSession, session_id)
    if session is None:
        raise http_not_found("Session not found")

    # Delete all messages in the session (cascades to citations)
    await db.execute(delete(Message).where(Message.session_id == session_id))
    # Also delete research entities linked to this session
    await db.execute(delete(ResearchEntity).where(ResearchEntity.session_id == session_id))
    await db.commit()
    return None

