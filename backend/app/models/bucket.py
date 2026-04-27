from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Bucket(Base):
    __tablename__ = "buckets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    tokens: Mapped[list["BucketToken"]] = relationship("BucketToken", back_populates="bucket", cascade="all, delete-orphan")


class BucketToken(Base):
    __tablename__ = "bucket_tokens"
    __table_args__ = (UniqueConstraint("bucket_id", "character_id", name="uq_bucket_character"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bucket_id: Mapped[int] = mapped_column(Integer, ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    bucket: Mapped["Bucket"] = relationship("Bucket", back_populates="tokens")
    character: Mapped["Character"] = relationship("Character", back_populates="bucket_token")


from app.models.character import Character  # noqa: E402, F401
