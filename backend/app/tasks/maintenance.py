from datetime import UTC, datetime, timedelta

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.maintenance.cleanup_task_runs", queue="default")
def cleanup_task_runs():
    """Delete TaskRun records older than 30 days."""
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    cutoff = datetime.now(UTC) - timedelta(days=30)
    sync_url = settings.db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM task_runs WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
    return {"deleted": result.rowcount, "cutoff": cutoff.isoformat()}
