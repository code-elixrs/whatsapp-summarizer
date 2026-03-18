from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.transcript import Transcript


class TranscriptSegmentResponse(BaseModel):
    id: uuid.UUID
    start_time: float
    end_time: float
    text: str
    segment_index: int

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    id: uuid.UUID
    media_item_id: uuid.UUID
    full_text: str
    language: str | None
    segments: list[TranscriptSegmentResponse]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, transcript: Transcript) -> TranscriptResponse:
        return cls(
            id=transcript.id,
            media_item_id=transcript.media_item_id,
            full_text=transcript.full_text,
            language=transcript.language,
            segments=[
                TranscriptSegmentResponse(
                    id=s.id,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    text=s.text,
                    segment_index=s.segment_index,
                )
                for s in sorted(transcript.segments, key=lambda s: s.segment_index)
            ],
            created_at=transcript.created_at,
        )
