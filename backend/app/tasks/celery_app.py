from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "helm",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.characters.wallet",
        "app.tasks.characters.skills",
        "app.tasks.characters.assets",
        "app.tasks.characters.mail",
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
        "app.tasks.high.*": {"queue": "high"},
    },
    beat_schedule={
        "update-all-wallets": {
            "task": "app.tasks.characters.wallet.update_all_wallets",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
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
        "update-all-mail": {
            "task": "app.tasks.characters.mail.update_all_mail",
            "schedule": 3600.0,
            "options": {"queue": "characters"},
        },
    },
)
