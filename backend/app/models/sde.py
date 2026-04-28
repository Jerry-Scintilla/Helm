"""SDE database models supporting multi-language JSONB storage."""
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SDEType(Base):
    """Item/skill type definitions with embedded multi-language names and descriptions."""

    __tablename__ = "sde_type"

    type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # _key from JSONL
    name: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"en": "...", "zh": "..."}
    description: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"en": "...", "zh": "..."}
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    market_group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icon_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SDEGroup(Base):
    """Item group definitions with embedded multi-language names."""

    __tablename__ = "sde_group"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # _key from JSONL
    name: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"en": "...", "zh": "..."}
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class SDECategory(Base):
    """Item category definitions with embedded multi-language names."""

    __tablename__ = "sde_category"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # _key from JSONL
    name: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"en": "...", "zh": "..."}
    published: Mapped[bool] = mapped_column(Boolean, default=False)
