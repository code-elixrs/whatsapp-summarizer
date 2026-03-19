import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


async def _poll_task_progress(
    websocket: WebSocket,
    item_id: str,
    redis_key_prefix: str,
    processing_state: str,
    processing_label: str,
):
    """Generic WebSocket poller for Celery task progress.

    Args:
        redis_key_prefix: Redis key prefix for task_id mapping (e.g. "transcription_task").
        processing_state: The custom Celery state name (e.g. "TRANSCRIBING", "OCR_PROCESSING").
        processing_label: Label sent to client (e.g. "transcribing", "ocr_processing").
    """
    await websocket.accept()

    try:
        last_state = None
        last_progress = -1
        poll_interval = 1.0

        while True:
            task_status = await _get_task_status(
                item_id, redis_key_prefix, processing_state, processing_label
            )

            if task_status != last_state or task_status.get("progress", 0) != last_progress:
                last_state = task_status
                last_progress = task_status.get("progress", 0)
                await websocket.send_json(task_status)

            status = task_status.get("status", "")
            if status in ("completed", "failed", "not_found"):
                break

            await asyncio.sleep(poll_interval)

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected for item %s", item_id)
    except Exception:
        logger.exception("WebSocket error for item %s", item_id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@router.websocket("/ws/transcription/{item_id}")
async def transcription_status(websocket: WebSocket, item_id: str):
    """WebSocket endpoint that streams transcription progress for a media item."""
    await _poll_task_progress(
        websocket, item_id,
        redis_key_prefix="transcription_task",
        processing_state="TRANSCRIBING",
        processing_label="transcribing",
    )


@router.websocket("/ws/ocr/{item_id}")
async def ocr_status(websocket: WebSocket, item_id: str):
    """WebSocket endpoint that streams OCR progress for a screenshot item."""
    await _poll_task_progress(
        websocket, item_id,
        redis_key_prefix="ocr_task",
        processing_state="OCR_PROCESSING",
        processing_label="ocr_processing",
    )


@router.websocket("/ws/stitch/{group_id}")
async def stitch_status(websocket: WebSocket, group_id: str):
    """WebSocket endpoint that streams stitching progress for a group."""
    await _poll_task_progress(
        websocket, group_id,
        redis_key_prefix="stitch_task",
        processing_state="STITCHING",
        processing_label="stitching",
    )


async def _get_task_status(
    item_id: str,
    redis_key_prefix: str,
    processing_state: str,
    processing_label: str,
) -> dict:
    """Check Celery for task status for the given item."""
    try:
        from redis import Redis
        from app.core.config import settings

        redis_client = Redis.from_url(settings.REDIS_URL)
        task_id = redis_client.get(f"{redis_key_prefix}:{item_id}")
        redis_client.close()

        if task_id:
            task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
            result = celery_app.AsyncResult(task_id)

            if result.state == "PENDING":
                return {"status": "pending", "progress": 0, "item_id": item_id}
            elif result.state == processing_state:
                meta = result.info or {}
                return {
                    "status": processing_label,
                    "progress": meta.get("progress", 0),
                    "segments_done": meta.get("segments_done", 0),
                    "item_id": item_id,
                }
            elif result.state == "SUCCESS":
                return {
                    "status": "completed",
                    "progress": 100,
                    "item_id": item_id,
                    "result": result.result,
                }
            elif result.state == "FAILURE":
                return {
                    "status": "failed",
                    "progress": 0,
                    "item_id": item_id,
                    "error": str(result.info),
                }
            else:
                return {
                    "status": result.state.lower(),
                    "progress": 0,
                    "item_id": item_id,
                }
    except Exception as exc:
        logger.debug("Error checking task status: %s", exc)

    return {"status": "not_found", "progress": 0, "item_id": item_id}
