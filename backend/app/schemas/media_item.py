import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.media_item import ContentType, ProcessingStatus, TimestampSource


class MediaItemCreate(BaseModel):
    content_type: ContentType
    title: str | None = None
    notes: str | None = None
    item_timestamp: datetime | None = None
    timestamp_source: TimestampSource = TimestampSource.USER_PROVIDED
    group_id: uuid.UUID | None = None
    group_order: int | None = None
    platform: str | None = Field(default=None, max_length=50)


class MediaItemUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    content_type: ContentType | None = None
    item_timestamp: datetime | None = None
    timestamp_source: TimestampSource | None = None
    platform: str | None = Field(default=None, max_length=50)


class MediaItemResponse(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    content_type: ContentType
    title: str | None
    notes: str | None
    file_name: str
    file_size: int
    mime_type: str
    item_timestamp: datetime | None
    timestamp_source: TimestampSource
    processing_status: ProcessingStatus
    group_id: uuid.UUID | None
    group_order: int | None
    stitched_path: str | None
    platform: str | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime
    file_url: str

    model_config = {"from_attributes": True}


class MediaItemListResponse(BaseModel):
    items: list[MediaItemResponse]
    total: int
