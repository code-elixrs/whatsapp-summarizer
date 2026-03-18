import uuid

from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str | None] = mapped_column(nullable=True)

    media_item: Mapped["MediaItem"] = relationship(back_populates="transcript")  # noqa: F821
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan", order_by="TranscriptSegment.start_time"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)

    transcript: Mapped["Transcript"] = relationship(back_populates="segments")
