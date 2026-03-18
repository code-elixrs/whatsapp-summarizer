import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/transcription/{item_id}")
async def transcription_status(websocket: WebSocket, item_id: str):
    """WebSocket endpoint that streams transcription progress for a media item.

    Clients connect and receive JSON messages with task progress updates.
    The connection closes automatically when transcription completes or fails.
    """
    await websocket.accept()

    try:
        # Find the active task for this item by checking Celery's result backend
        # We poll the task state periodically and push updates to the client
        last_state = None
        last_progress = -1
        poll_interval = 1.0  # seconds

        while True:
            # Check all active/reserved tasks to find one for this item
            task_status = await _get_task_status_for_item(item_id)

            if task_status != last_state or task_status.get("progress", 0) != last_progress:
                last_state = task_status
                last_progress = task_status.get("progress", 0)
                await websocket.send_json(task_status)

            # Stop polling if terminal state
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


async def _get_task_status_for_item(item_id: str) -> dict:
    """Check Celery for active transcription task status for the given item."""
    # Use the inspect API to find tasks, or check result backend
    # Since we use item_id as the first arg, we can search by inspecting active tasks
    # For simplicity, we'll use the AsyncResult with a predictable task ID pattern

    # Check if there's a result stored for this item
    # We use Redis to store a mapping from item_id -> task_id
    try:
        from redis import Redis
        from app.core.config import settings

        redis_client = Redis.from_url(settings.REDIS_URL)
        task_id = redis_client.get(f"transcription_task:{item_id}")
        redis_client.close()

        if task_id:
            task_id = task_id.decode() if isinstance(task_id, bytes) else task_id
            result = celery_app.AsyncResult(task_id)

            if result.state == "PENDING":
                return {"status": "pending", "progress": 0, "item_id": item_id}
            elif result.state == "TRANSCRIBING":
                meta = result.info or {}
                return {
                    "status": "transcribing",
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
