import asyncio

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_process_shutdown

from lib.core.container import container


app = Celery(
    "digest_worker",
    broker=container.settings.redis_url,
    backend=container.settings.redis_url,
    include=["lib.worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",  # GMT+3
    enable_utc=False,
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
    container.db.init()


@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    if "db" not in container.__dict__:
        return

    loop = asyncio.get_event_loop()
    loop.run_until_complete(container.close())
