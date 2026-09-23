import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Document
from app.rag.ingestion import run_ingestion
from app.core.errors import http_not_found

router = APIRouter()

ALLOWED_TYPES = {"pdf", "docx", "doc", "txt"}


class DocumentOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    original_filename: str
    file_type: str
    status: str
    error_message: str | None
    page_count: int | None
    case_name: str | None
    uploaded_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_TYPES:
        return JSONResponse(status_code=400, content={"detail": f"Unsupported file type: {ext}. Allowed: {ALLOWED_TYPES}"})

    file_data = await file.read()

    doc = Document(
        session_id=session_id,
        original_filename=file.filename,
        file_type=ext,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Kick off ingestion in the background — endpoint returns immediately
    background_tasks.add_task(run_ingestion, doc.id, file_data, ext)

    return doc


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.session_id == session_id).order_by(Document.uploaded_at)
    )
    return result.scalars().all()


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise http_not_found("Document not found")
    await db.delete(doc)
    await db.commit()
