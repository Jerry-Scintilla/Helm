from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.task_run import TaskRun
from app.models.user import User
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/v1/admin/tasks", tags=["admin-tasks"])


# ── Task History ──────────────────────────────────────────────────────────────

@router.get("/")
async def list_task_runs(
    status: Optional[str] = Query(None),
    task_name: Optional[str] = Query(None),
    queue: Optional[str] = Query(None),
    triggered_by: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    q = select(TaskRun)
    if status:
        q = q.where(TaskRun.status == status)
    if task_name:
        q = q.where(TaskRun.task_name.ilike(f"%{task_name}%"))
    if queue:
        q = q.where(TaskRun.queue == queue)
    if triggered_by:
        q = q.where(TaskRun.triggered_by == triggered_by)
    if date_from:
        q = q.where(TaskRun.created_at >= date_from)
    if date_to:
        q = q.where(TaskRun.created_at <= date_to)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar() or 0

    q = q.order_by(desc(TaskRun.created_at)).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_run(r) for r in rows],
    }


@router.get("/stats")
async def get_task_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    since = datetime.now(UTC) - timedelta(hours=24)

    counts_result = await db.execute(
        select(TaskRun.status, func.count().label("cnt"))
        .where(TaskRun.created_at >= since)
        .group_by(TaskRun.status)
    )
    counts = {row.status: row.cnt for row in counts_result}

    running_result = await db.execute(
        select(func.count()).where(TaskRun.status.in_(["running", "pending"]))
    )
    running_total = running_result.scalar() or 0

    # Average duration (seconds) per task_name in last 24h, top 10 slowest
    avg_result = await db.execute(
        select(
            TaskRun.task_name,
            func.avg(
                func.extract("epoch", TaskRun.completed_at) - func.extract("epoch", TaskRun.started_at)
            ).label("avg_duration"),
            func.count().label("cnt"),
        )
        .where(
            TaskRun.created_at >= since,
            TaskRun.status == "success",
            TaskRun.started_at.is_not(None),
            TaskRun.completed_at.is_not(None),
        )
        .group_by(TaskRun.task_name)
        .order_by(desc("avg_duration"))
        .limit(10)
    )
    slowest = [
        {"task_name": row.task_name, "avg_duration_seconds": round(float(row.avg_duration), 2), "count": row.cnt}
        for row in avg_result
        if row.avg_duration is not None
    ]

    return {
        "last_24h": {
            "success": counts.get("success", 0),
            "failure": counts.get("failure", 0),
            "retry": counts.get("retry", 0),
            "revoked": counts.get("revoked", 0),
        },
        "currently_active": running_total,
        "slowest_tasks": slowest,
    }


@router.get("/scheduled")
async def list_scheduled_tasks(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    beat = celery_app.conf.beat_schedule
    result = []

    for name, entry in beat.items():
        task_name = entry["task"]
        schedule_seconds = float(entry.get("schedule", 0))
        queue = entry.get("options", {}).get("queue", "default")

        # Last completed run for this task
        last_run_row = (
            await db.execute(
                select(TaskRun)
                .where(TaskRun.task_name == task_name)
                .where(TaskRun.status.in_(["success", "failure", "revoked"]))
                .order_by(desc(TaskRun.completed_at))
                .limit(1)
            )
        ).scalar_one_or_none()

        last_run = None
        estimated_next_run = None
        if last_run_row:
            last_run = {
                "task_id": last_run_row.task_id,
                "status": last_run_row.status,
                "completed_at": last_run_row.completed_at.isoformat() if last_run_row.completed_at else None,
                "duration_seconds": _duration(last_run_row),
            }
            if last_run_row.completed_at and schedule_seconds:
                estimated_next_run = (
                    last_run_row.completed_at + timedelta(seconds=schedule_seconds)
                ).isoformat()

        result.append({
            "name": name,
            "task": task_name,
            "queue": queue,
            "schedule_seconds": schedule_seconds,
            "last_run": last_run,
            "estimated_next_run": estimated_next_run,
        })

    result.sort(key=lambda x: x["name"])
    return result


@router.post("/scheduled/{name}/trigger")
async def trigger_scheduled_task(
    name: str,
    _: User = Depends(require_permission("global.superuser")),
):
    beat = celery_app.conf.beat_schedule
    if name not in beat:
        raise HTTPException(status_code=404, detail=f"Scheduled task '{name}' not found")

    entry = beat[name]
    task_name = entry["task"]
    queue = entry.get("options", {}).get("queue", "default")

    ar = celery_app.send_task(
        task_name,
        queue=queue,
        headers={"x_triggered_by": "manual"},
    )
    return {"task_id": ar.id, "task_name": task_name, "queue": queue}


# ── Individual Task ───────────────────────────────────────────────────────────

@router.get("/{task_id}")
async def get_task_run(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("global.superuser")),
):
    row = (await db.execute(select(TaskRun).where(TaskRun.task_id == task_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_run(row, full=True)


@router.post("/{task_id}/revoke")
async def revoke_task(
    task_id: str,
    _: User = Depends(require_permission("global.superuser")),
):
    celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
    return {"task_id": task_id, "revoked": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _duration(run: TaskRun) -> float | None:
    if run.started_at and run.completed_at:
        return round((run.completed_at - run.started_at).total_seconds(), 2)
    return None


def _serialize_run(run: TaskRun, full: bool = False) -> dict:
    d = {
        "task_id": run.task_id,
        "task_name": run.task_name,
        "queue": run.queue,
        "status": run.status,
        "triggered_by": run.triggered_by,
        "retry_count": run.retry_count,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": _duration(run),
    }
    if full:
        d["result"] = run.result
        d["error"] = run.error
    return d
