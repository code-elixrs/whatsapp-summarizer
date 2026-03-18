import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SpaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    color: str = Field(default="#7c3aed", pattern=r"^#[0-9a-fA-F]{6}$")


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class SpaceItemCounts(BaseModel):
    calls: int = 0
    chats: int = 0
    statuses: int = 0
    media: int = 0


class SpaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    color: str
    created_at: datetime
    updated_at: datetime
    item_counts: SpaceItemCounts = SpaceItemCounts()

    model_config = {"from_attributes": True}


class SpaceListResponse(BaseModel):
    spaces: list[SpaceResponse]
    total: int
