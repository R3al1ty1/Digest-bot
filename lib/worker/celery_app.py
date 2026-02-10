from celery import Celery
from celery.schedules import crontab

from lib.core.config import settings


app = Celery(
    "digest_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["lib.worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,  # Process one task at a time
)

# Celery Beat schedule
app.conf.beat_schedule = {
    "daily-digest": {
        "task": "lib.worker.tasks.scheduled_digest_task",
        "schedule": crontab(
            hour=settings.digest_hour,
            minute=settings.digest_minute,
        ),
    },
}
