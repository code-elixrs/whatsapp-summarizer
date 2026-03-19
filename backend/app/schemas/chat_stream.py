from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ChatStreamMessage(BaseModel):
    """A chat message entry in the unified stream."""
    type: Literal["message"] = "message"
    id: uuid.UUID
    sender: str | None
    message: str
    message_timestamp: datetime | None
    message_order: int
    is_sent: bool
    source_item_id: uuid.UUID
    source_group_id: uuid.UUID | None
    sort_key: datetime


class ChatStreamEvent(BaseModel):
    """An event marker (call, status, media) in the unified stream."""
    type: Literal["event"] = "event"
    event_type: str  # "call_recording", "status_update", "other_media"
    item_id: uuid.UUID
    title: str | None
    file_name: str
    mime_type: str
    platform: str | None
    duration_seconds: int | None
    item_timestamp: datetime | None
    file_url: str
    transcript_summary: str | None = None
    sort_key: datetime


class ChatStreamResponse(BaseModel):
    entries: list[ChatStreamMessage | ChatStreamEvent]
    total_messages: int
    total_events: int
