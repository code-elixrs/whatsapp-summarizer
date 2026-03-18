from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Space(Base):
    __tablename__ = "spaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#7c3aed")

    items: Mapped[list["MediaItem"]] = relationship(  # noqa: F821
        back_populates="space", cascade="all, delete-orphan"
    )
