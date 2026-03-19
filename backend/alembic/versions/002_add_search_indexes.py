"""add search indexes

Revision ID: 002
Revises: 001
Create Date: 2026-03-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # GIN indexes for full-text search
    op.execute(
        "CREATE INDEX ix_chat_messages_fts ON chat_messages "
        "USING gin(to_tsvector('english', coalesce(sender, '') || ' ' || message))"
    )
    op.execute(
        "CREATE INDEX ix_transcripts_fts ON transcripts "
        "USING gin(to_tsvector('english', full_text))"
    )
    op.execute(
        "CREATE INDEX ix_media_items_fts ON media_items "
        "USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(notes, '') || ' ' || file_name))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_fts")
    op.execute("DROP INDEX IF EXISTS ix_transcripts_fts")
    op.execute("DROP INDEX IF EXISTS ix_media_items_fts")
