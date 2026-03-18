import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_sent: Mapped[bool] = mapped_column(default=False)

    media_item: Mapped["MediaItem"] = relationship(back_populates="chat_messages")  # noqa: F821
