import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ContentType(str, enum.Enum):
    CALL_RECORDING = "call_recording"
    CHAT_SCREENSHOT = "chat_screenshot"
    STATUS_UPDATE = "status_update"
    OTHER_MEDIA = "other_media"


class TimestampSource(str, enum.Enum):
    AUTO_DETECTED = "auto_detected"
    USER_PROVIDED = "user_provided"
    FILE_METADATA = "file_metadata"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaItem(Base):
    __tablename__ = "media_items"

    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False
    )
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    item_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timestamp_source: Mapped[TimestampSource] = mapped_column(
        Enum(TimestampSource, values_callable=lambda e: [x.value for x in e]),
        default=TimestampSource.USER_PROVIDED,
    )

    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, values_callable=lambda e: [x.value for x in e]),
        default=ProcessingStatus.PENDING,
    )

    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    group_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stitched_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    space: Mapped["Space"] = relationship(back_populates="items")  # noqa: F821
    transcript: Mapped["Transcript | None"] = relationship(  # noqa: F821
        back_populates="media_item", cascade="all, delete-orphan", uselist=False
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        back_populates="media_item", cascade="all, delete-orphan"
    )
