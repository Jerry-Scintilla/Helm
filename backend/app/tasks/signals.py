"""
Celery signal handlers that write task execution history to PostgreSQL.
Runs synchronously inside the worker process — uses a psycopg2 sync engine.
"""
import json
import logging
from datetime import UTC, datetime

from celery.signals import task_failure, task_prerun, task_retry, task_revoked, task_success, worker_init
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_SessionFactory = None

# Beat-scheduled task names (used to detect triggered_by="scheduled")
_BEAT_TASK_NAMES: set[str] = set()


def _get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        # Replace asyncpg driver with psycopg2 for sync access in worker
        sync_url = settings.db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        engine = create_engine(sync_url, pool_pre_ping=True, pool_size=2, max_overflow=2)
        _SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionFactory


def _get_beat_task_names() -> set[str]:
    """Lazily load beat task names from celery config."""
    global _BEAT_TASK_NAMES
    if not _BEAT_TASK_NAMES:
        try:
            from app.tasks.celery_app import celery_app
            _BEAT_TASK_NAMES = {v["task"] for v in celery_app.conf.beat_schedule.values()}
        except Exception:
            pass
    return _BEAT_TASK_NAMES


def _resolve_triggered_by(task) -> str:
    try:
        headers = task.request.headers or {}
        if headers.get("x_triggered_by") == "manual":
            return "manual"
        if task.name in _get_beat_task_names():
            return "scheduled"
    except Exception:
        pass
    return "system"


def _upsert_task_run(session, task_id: str, **fields) -> None:
    """Insert or update a task_run row by task_id."""
    existing = session.execute(
        text("SELECT id FROM task_runs WHERE task_id = :tid"),
        {"tid": task_id},
    ).fetchone()

    if existing:
        set_clauses = ", ".join(f"{k} = :{k}" for k in fields)
        session.execute(
            text(f"UPDATE task_runs SET {set_clauses} WHERE task_id = :task_id"),
            {"task_id": task_id, **fields},
        )
    else:
        cols = ["task_id"] + list(fields.keys())
        vals = [":task_id"] + [f":{k}" for k in fields.keys()]
        session.execute(
            text(f"INSERT INTO task_runs ({', '.join(cols)}) VALUES ({', '.join(vals)})"),
            {"task_id": task_id, **fields},
        )


@worker_init.connect
def on_worker_init(**kwargs):
    from app.esi.client import register_token_persist
    from app.core.token_persist import persist_refreshed_token
    register_token_persist(persist_refreshed_token)
    _load_plugin_tasks()


def _load_plugin_tasks() -> None:
    """Import plugin task modules into the worker process at startup.

    _register_celery_tasks() runs in the FastAPI process and has no effect on
    worker processes.  Workers only know about tasks imported at startup.  This
    function queries the DB for enabled plugins and imports each plugin's task
    modules so that tasks dispatched via .delay() can actually be executed.
    """
    import importlib

    try:
        Session = _get_session_factory()
        with Session() as session:
            rows = session.execute(
                text(
                    "SELECT entry_point FROM plugins"
                    " WHERE is_enabled = TRUE AND status = 'enabled'"
                )
            ).fetchall()
    except Exception as exc:
        logger.warning("worker_init: could not query plugins from DB: %s", exc)
        return

    for (entry_point,) in rows:
        try:
            from app.plugins.installer import load_plugin_class
            plugin_class = load_plugin_class(entry_point)
            plugin_instance = plugin_class()
            for module_path in plugin_instance.get_tasks():
                try:
                    importlib.import_module(module_path)
                    logger.info("worker_init: loaded plugin task module '%s'", module_path)
                except Exception as exc:
                    logger.warning(
                        "worker_init: failed to import plugin task module '%s': %s",
                        module_path, exc,
                    )
        except Exception as exc:
            logger.warning("worker_init: failed to load plugin '%s': %s", entry_point, exc)


@task_prerun.connect
def on_task_prerun(task_id, task, args, kwargs, **kw):
    try:
        Session = _get_session_factory()
        with Session() as session:
            _upsert_task_run(
                session,
                task_id=task_id,
                task_name=task.name,
                queue=task.request.delivery_info.get("routing_key", "default") if task.request.delivery_info else "default",
                status="running",
                triggered_by=_resolve_triggered_by(task),
                started_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                retry_count=task.request.retries or 0,
            )
            session.commit()
    except Exception:
        logger.exception("task_prerun signal failed for %s", task_id)


@task_success.connect
def on_task_success(sender, result, **kw):
    try:
        task_id = sender.request.id
        result_str = None
        if result is not None:
            try:
                result_str = json.dumps(result)[:2000]
            except Exception:
                result_str = str(result)[:2000]

        Session = _get_session_factory()
        with Session() as session:
            _upsert_task_run(
                session,
                task_id=task_id,
                task_name=sender.name,
                queue=sender.request.delivery_info.get("routing_key", "default") if sender.request.delivery_info else "default",
                status="success",
                triggered_by=_resolve_triggered_by(sender),
                result=result_str,
                completed_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                retry_count=sender.request.retries or 0,
            )
            session.commit()
    except Exception:
        logger.exception("task_success signal failed for %s", sender.request.id)


@task_failure.connect
def on_task_failure(task_id, exception, traceback, sender, **kw):
    try:
        import traceback as tb_mod
        error_str = "".join(tb_mod.format_exception(type(exception), exception, traceback))[:4000]

        Session = _get_session_factory()
        with Session() as session:
            _upsert_task_run(
                session,
                task_id=task_id,
                task_name=sender.name,
                queue=sender.request.delivery_info.get("routing_key", "default") if sender.request.delivery_info else "default",
                status="failure",
                triggered_by=_resolve_triggered_by(sender),
                error=error_str,
                completed_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                retry_count=sender.request.retries or 0,
            )
            session.commit()
    except Exception:
        logger.exception("task_failure signal failed for %s", task_id)


@task_retry.connect
def on_task_retry(request, reason, einfo, **kw):
    try:
        task_id = request.id
        error_str = str(reason)[:4000] if reason else None

        Session = _get_session_factory()
        with Session() as session:
            session.execute(
                text("""
                    UPDATE task_runs
                    SET status = 'retry',
                        retry_count = retry_count + 1,
                        error = :error
                    WHERE task_id = :task_id
                """),
                {"task_id": task_id, "error": error_str},
            )
            session.commit()
    except Exception:
        logger.exception("task_retry signal failed for %s", request.id)


@task_revoked.connect
def on_task_revoked(request, terminated, signum, expired, **kw):
    try:
        task_id = request.id
        Session = _get_session_factory()
        with Session() as session:
            session.execute(
                text("""
                    UPDATE task_runs
                    SET status = 'revoked', completed_at = :now
                    WHERE task_id = :task_id
                """),
                {"task_id": task_id, "now": datetime.now(UTC)},
            )
            session.commit()
    except Exception:
        logger.exception("task_revoked signal failed for %s", request.id)
