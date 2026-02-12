import asyncio

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

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
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "hourly-digest-check": {
        "task": "lib.worker.tasks.scheduled_digest_task",
        "schedule": crontab(minute=0),
    },
}


@worker_process_init.connect
def init_worker_process(**kwargs):
    """
    Create a single event loop for each worker process.
    This loop will be reused for all async tasks in this process.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
