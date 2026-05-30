from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "helm",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.characters.wallet",
        "app.tasks.characters.info",
        "app.tasks.characters.skills",
        "app.tasks.characters.assets",
        "app.tasks.characters.mail",
        "app.tasks.characters.wallet_journal",
        "app.tasks.characters.wallet_transactions",
        "app.tasks.characters.skill_queue",
        "app.tasks.characters.notifications",
        "app.tasks.characters.structures",
        "app.tasks.characters.contracts",
        "app.tasks.characters.killmails",
        "app.tasks.corporations.info",
        "app.tasks.corporations.members",
        "app.tasks.corporations.wallet",
        "app.tasks.corporations.assets",
        "app.tasks.alliances.info",
        "app.tasks.sde.import_sde",
        "app.tasks.sde.refresh_icon_cache",
        "app.tasks.bucket.scheduler",
        "app.tasks.bucket.runner",
        "app.tasks.bucket.backfill",
        "app.tasks.esi_cache.refresh",
        "app.tasks.maintenance",
        "app.tasks.marketplace",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "app.tasks.characters.*": {"queue": "characters"},
        "app.tasks.corporations.*": {"queue": "corporations"},
        "app.tasks.alliances.*": {"queue": "corporations"},
        "app.tasks.bucket.*": {"queue": "bucket"},
        "app.tasks.high.*": {"queue": "high"},
        "app.tasks.sde.*": {"queue": "high"},
        # Plugin tasks — all unrecognised prefixes land on the default queue.
        # Each plugin may override this via @celery_app.task(queue="...").
    },
    beat_schedule={
        # Character per-character refresh is fully handled by the bucket scheduler.
        # Corporation tasks — hourly
        "sync-all-corporations": {
            "task": "app.tasks.corporations.info.sync_all_corporations",
            "schedule": 3600.0,
            "options": {"queue": "corporations"},
        },
        "sync-all-corporation-members": {
            "task": "app.tasks.corporations.members.sync_all_corporation_members",
            "schedule": 3600.0,
            "options": {"queue": "corporations"},
        },
        "sync-all-corporation-wallets": {
            "task": "app.tasks.corporations.wallet.sync_all_corporation_wallets",
            "schedule": 3600.0,
            "options": {"queue": "corporations"},
        },
        "sync-all-corporation-assets": {
            "task": "app.tasks.corporations.assets.sync_all_corporation_assets",
            "schedule": 3600.0,
            "options": {"queue": "corporations"},
        },
        # Alliance tasks — daily
        "sync-all-alliances": {
            "task": "app.tasks.alliances.info.sync_all_alliances",
            "schedule": 86400.0,
            "options": {"queue": "corporations"},
        },
        # Bucket scheduler — every 10 minutes
        "bucket-scheduler": {
            "task": "app.tasks.bucket.scheduler.run_bucket_scheduler",
            "schedule": 600.0,
            "options": {"queue": "bucket"},
        },
        # Maintenance — daily cleanup of task_runs older than 30 days
        "cleanup-old-task-runs": {
            "task": "app.tasks.maintenance.cleanup_task_runs",
            "schedule": 86400.0,
        },
        # Marketplace index refresh — every 6 hours
        "refresh-marketplace-index": {
            "task": "app.tasks.marketplace.refresh_marketplace_index",
            "schedule": 21600.0,
        },
    },
)

# Register Celery signal handlers for task history tracking
from app.tasks import signals  # noqa: E402, F401
