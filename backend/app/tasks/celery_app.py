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
        "app.tasks.corporations.info",
        "app.tasks.corporations.members",
        "app.tasks.corporations.wallet",
        "app.tasks.corporations.assets",
        "app.tasks.alliances.info",
        "app.tasks.sde.import_sde",
        "app.tasks.bucket.scheduler",
        "app.tasks.bucket.runner",
        "app.tasks.esi_cache.refresh",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.characters.*": {"queue": "characters"},
        "app.tasks.corporations.*": {"queue": "corporations"},
        "app.tasks.alliances.*": {"queue": "corporations"},
        "app.tasks.bucket.*": {"queue": "bucket"},
        "app.tasks.high.*": {"queue": "high"},
        "app.tasks.sde.*": {"queue": "high"},
    },
    beat_schedule={
        # Character tasks — hourly
        "update-all-wallets": {
            "task": "app.tasks.characters.wallet.update_all_wallets",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
        "update-all-wallet-journals": {
            "task": "app.tasks.characters.wallet_journal.update_all_wallet_journals",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
        "update-all-wallet-transactions": {
            "task": "app.tasks.characters.wallet_transactions.update_all_wallet_transactions",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
        "update-all-skill-queues": {
            "task": "app.tasks.characters.skill_queue.update_all_skill_queues",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
        "update-all-notifications": {
            "task": "app.tasks.characters.notifications.update_all_notifications",
            "schedule": 1800.0,  # 30 minutes per spec
            "options": {"queue": "characters"},
        },
        "update-all-mail": {
            "task": "app.tasks.characters.mail.update_all_mail",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
        # Character tasks — daily
        "update-all-skills": {
            "task": "app.tasks.characters.skills.update_all_skills",
            "schedule": 86400.0,
            "options": {"queue": "characters"},
        },
        "update-all-assets": {
            "task": "app.tasks.characters.assets.update_all_assets",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
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
        # Bucket scheduler — every minute
        "bucket-scheduler": {
            "task": "app.tasks.bucket.scheduler.run_bucket_scheduler",
            "schedule": 60.0,
            "options": {"queue": "bucket"},
        },
        # Maintenance — daily cleanup of task_runs older than 30 days
        "cleanup-old-task-runs": {
            "task": "app.tasks.maintenance.cleanup_task_runs",
            "schedule": 86400.0,
        },
    },
)

# Register Celery signal handlers for task history tracking
from app.tasks import signals  # noqa: E402, F401
