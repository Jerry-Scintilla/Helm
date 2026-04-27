from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alliance(Base):
    __tablename__ = "alliances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alliance_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    creator_corp_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    executor_corp_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    member_corporations: Mapped[list["AllianceCorporation"]] = relationship(
        "AllianceCorporation", back_populates="alliance", cascade="all, delete-orphan"
    )


class AllianceCorporation(Base):
    __tablename__ = "alliance_corporations"
    __table_args__ = (UniqueConstraint("alliance_id", "corporation_id", name="uq_alliance_corp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alliance_id: Mapped[int] = mapped_column(Integer, ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False, index=True)
    corporation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    alliance: Mapped["Alliance"] = relationship("Alliance", back_populates="member_corporations")
