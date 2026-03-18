"""initial models

Revision ID: 001
Revises:
Create Date: 2026-03-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#7c3aed"),
        sa.PrimaryKeyConstraint("id"),
    )

    content_type_enum = postgresql.ENUM(
        "call_recording", "chat_screenshot", "status_update", "other_media",
        name="contenttype", create_type=True,
    )
    timestamp_source_enum = postgresql.ENUM(
        "auto_detected", "user_provided", "file_metadata",
        name="timestampsource", create_type=True,
    )
    processing_status_enum = postgresql.ENUM(
        "pending", "processing", "completed", "failed",
        name="processingstatus", create_type=True,
    )

    op.create_table(
        "media_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", content_type_enum, nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("item_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp_source", timestamp_source_enum, nullable=True),
        sa.Column("processing_status", processing_status_enum, nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_order", sa.Integer(), nullable=True),
        sa.Column("stitched_path", sa.String(1000), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_items_group_id", "media_items", ["group_id"])

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("language", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["media_item_id"], ["media_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_item_id"),
    )

    op.create_table(
        "transcript_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("transcript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("message_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["media_item_id"], ["media_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("transcript_segments")
    op.drop_table("transcripts")
    op.drop_index("ix_media_items_group_id", table_name="media_items")
    op.drop_table("media_items")
    op.drop_table("spaces")

    op.execute("DROP TYPE IF EXISTS contenttype")
    op.execute("DROP TYPE IF EXISTS timestampsource")
    op.execute("DROP TYPE IF EXISTS processingstatus")
