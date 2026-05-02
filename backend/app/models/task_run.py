from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskRun(Base):
    __tablename__ = "task_runs"
    __table_args__ = (
        Index("ix_task_runs_task_name_created", "task_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    task_name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    queue: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # pending / running / success / failure / revoked / retry
    triggered_by: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    # scheduled / manual / system
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
