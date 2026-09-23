"""Create all application tables.

Revision ID: 002
Revises: 001
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("case_name", sa.Text, nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('uploaded','processing','processed','failed')", name="ck_document_status"),
    )
    op.create_index("ix_documents_session_status", "documents", ["session_id", "status"])

    # document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("section", sa.Text, nullable=True),
        sa.Column("paragraph", sa.Text, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_document_index", "document_chunks", ["document_id", "chunk_index"])
    # HNSW vector index for semantic search
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops);"
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("routing_mode", sa.String(20), nullable=True),
        sa.Column("pipeline_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user','assistant')", name="ck_message_role"),
        sa.CheckConstraint("routing_mode IN ('document','web','combined') OR routing_mode IS NULL", name="ck_message_routing"),
    )
    op.create_index("ix_messages_session_created", "messages", ["session_id", "created_at"])

    # citations
    op.create_table(
        "citations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("court_or_authority", sa.Text, nullable=True),
        sa.Column("citation_date", sa.Date, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("page_number", sa.Text, nullable=True),
        sa.Column("section", sa.Text, nullable=True),
        sa.Column("paragraph", sa.Text, nullable=True),
        sa.Column("case_name", sa.Text, nullable=True),
        sa.Column("excerpt", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("source_type IN ('document','web')", name="ck_citation_source_type"),
    )
    op.create_index("ix_citations_message", "citations", ["message_id"])

    # research_entities
    op.create_table(
        "research_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source_message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("entity_type IN ('case','statute','issue','authority')", name="ck_entity_type"),
    )
    op.create_index("ix_entities_session_type", "research_entities", ["session_id", "entity_type"])

    # research_relationships
    op.create_table(
        "research_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_entity_id", UUID(as_uuid=True), sa.ForeignKey("research_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_entity_id", UUID(as_uuid=True), sa.ForeignKey("research_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("relationship_type", sa.String(40), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "relationship_type IN ('found_while_researching','distinguished','followed','conflicts_with','compared_to')",
            name="ck_relationship_type",
        ),
    )
    op.create_index("ix_relationships_session_from", "research_relationships", ["session_id", "from_entity_id"])


def downgrade() -> None:
    op.drop_table("research_relationships")
    op.drop_table("research_entities")
    op.drop_table("citations")
    op.drop_table("messages")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("sessions")
