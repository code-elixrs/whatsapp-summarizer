from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "lifelog",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"], related_name=None, force=True)

# Explicitly import task modules so Celery registers them
import app.tasks.transcribe  # noqa: F401, E402
import app.tasks.ocr  # noqa: F401, E402
import app.tasks.stitch  # noqa: F401, E402
