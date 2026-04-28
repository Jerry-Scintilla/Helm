from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    package_name: Mapped[str] = mapped_column(String(256), nullable=False)
    entry_point: Mapped[str] = mapped_column(String(512), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    author: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    helm_sdk_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # "installed" | "enabled" | "disabled" | "error" | "uninstalled"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="installed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON snapshot: esi_scopes, sidebar_items, widgets
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    frontend_bundle_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
