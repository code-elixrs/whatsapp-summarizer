from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    """A single search result."""
    result_type: Literal["chat_message", "transcript", "media_item"]
    item_id: uuid.UUID
    space_id: uuid.UUID
    space_name: str
    content_type: str
    title: str | None
    file_name: str
    snippet: str
    item_timestamp: datetime | None
    platform: str | None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int
