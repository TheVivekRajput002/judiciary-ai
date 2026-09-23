import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, CheckConstraint, func, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------
class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    research_entities: Mapped[list["ResearchEntity"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    research_relationships: Mapped[list["ResearchRelationship"]] = relationship(back_populates="session", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# documents
# ---------------------------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    original_filename: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(String(20))
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # null — raw files discarded
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    case_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('uploaded','processing','processed','failed')", name="ck_document_status"),
        Index("ix_documents_session_status", "session_id", "status"),
    )

    session: Mapped["Session"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    citations: Mapped[list["Citation"]] = relationship(back_populates="document")


# ---------------------------------------------------------------------------
# document_chunks
# ---------------------------------------------------------------------------
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paragraph: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")
    citations: Mapped[list["Citation"]] = relationship(back_populates="chunk")


# ---------------------------------------------------------------------------
# messages
# ---------------------------------------------------------------------------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    routing_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pipeline_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="ck_message_role"),
        CheckConstraint("routing_mode IN ('document','web','combined') OR routing_mode IS NULL", name="ck_message_routing"),
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    session: Mapped["Session"] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(back_populates="message", cascade="all, delete-orphan")
    research_entities: Mapped[list["ResearchEntity"]] = relationship(back_populates="source_message")


# ---------------------------------------------------------------------------
# citations
# ---------------------------------------------------------------------------
class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(20))
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    court_or_authority: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paragraph: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    case_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("source_type IN ('document','web')", name="ck_citation_source_type"),
        Index("ix_citations_message", "message_id"),
    )

    message: Mapped["Message"] = relationship(back_populates="citations")
    document: Mapped[Optional["Document"]] = relationship(back_populates="citations")
    chunk: Mapped[Optional["DocumentChunk"]] = relationship(back_populates="citations")


# ---------------------------------------------------------------------------
# research_entities
# ---------------------------------------------------------------------------
class ResearchEntity(Base):
    __tablename__ = "research_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    entity_type: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("entity_type IN ('case','statute','issue','authority')", name="ck_entity_type"),
        Index("ix_entities_session_type", "session_id", "entity_type"),
    )

    session: Mapped["Session"] = relationship(back_populates="research_entities")
    source_message: Mapped[Optional["Message"]] = relationship(back_populates="research_entities")
    from_relationships: Mapped[list["ResearchRelationship"]] = relationship(
        back_populates="from_entity",
        foreign_keys="ResearchRelationship.from_entity_id",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# research_relationships
# ---------------------------------------------------------------------------
class ResearchRelationship(Base):
    __tablename__ = "research_relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    from_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_entities.id", ondelete="CASCADE"))
    to_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("research_entities.id", ondelete="SET NULL"), nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(40))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('found_while_researching','distinguished','followed','conflicts_with','compared_to')",
            name="ck_relationship_type",
        ),
        Index("ix_relationships_session_from", "session_id", "from_entity_id"),
    )

    session: Mapped["Session"] = relationship(back_populates="research_relationships")
    from_entity: Mapped["ResearchEntity"] = relationship(
        back_populates="from_relationships",
        foreign_keys=[from_entity_id],
    )
    to_entity: Mapped[Optional["ResearchEntity"]] = relationship(
        foreign_keys=[to_entity_id],
    )
