"""Enable pgvector and pgcrypto extensions.

Revision ID: 001
Revises:
Create Date: 2026-09-23
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


def downgrade() -> None:
    # Extensions are shared resources — only drop in dev, never in prod
    pass
