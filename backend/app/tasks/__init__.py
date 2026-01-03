from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "alphha_dms",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.ocr_tasks",
        "app.tasks.notification_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    beat_schedule={
        "generate-daily-merkle-roots": {
            "task": "app.tasks.audit_tasks.generate_merkle_roots",
            "schedule": 3600.0,  # Every hour for demo, change to daily in production
        },
        "check-retention-policies": {
            "task": "app.tasks.retention_tasks.execute_retention_policies",
            "schedule": 86400.0,  # Daily
        },
        "send-expiry-notifications": {
            "task": "app.tasks.notification_tasks.send_expiry_notifications",
            "schedule": 86400.0,  # Daily
        },
    }
)
