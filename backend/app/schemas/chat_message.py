from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    media_item_id: uuid.UUID
    sender: str | None
    message: str
    message_timestamp: datetime | None
    message_order: int
    is_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageUpdate(BaseModel):
    sender: str | None = None
    message: str | None = None
    message_timestamp: datetime | None = None
    is_sent: bool | None = None


class ChatMessagesResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int
