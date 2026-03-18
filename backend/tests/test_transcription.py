import io
import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_item import MediaItem, ProcessingStatus
from app.models.transcript import Transcript, TranscriptSegment


# Create a mock transcribe module so the lazy import in items.py works
_mock_transcribe_module = ModuleType("app.tasks.transcribe")
_mock_task = MagicMock()
_mock_task.delay.return_value = MagicMock(id="fake-task-id")
_mock_transcribe_module.transcribe_audio = _mock_task
sys.modules["app.tasks.transcribe"] = _mock_transcribe_module


async def _create_space(client: AsyncClient) -> str:
    resp = await client.post("/api/spaces", json={"name": "Transcription Test"})
    return resp.json()["id"]


def _make_audio(name: str = "test.mp3", content: bytes = b"fake audio data"):
    return {"file": (name, io.BytesIO(content), "audio/mpeg")}


def _reset_mock():
    _mock_task.reset_mock()
    _mock_task.delay.return_value = MagicMock(id="fake-task-id")


@pytest.mark.asyncio
async def test_audio_upload_sets_pending_status(client: AsyncClient):
    """Audio uploads should set processing_status to pending and queue transcription."""
    _reset_mock()
    space_id = await _create_space(client)

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["processing_status"] == "pending"
    assert data["content_type"] == "call_recording"
    _mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_audio_upload_with_model_selection(client: AsyncClient):
    """Audio upload with whisper_model parameter passes model to task."""
    _reset_mock()
    space_id = await _create_space(client)

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording", "whisper_model": "small"},
    )

    assert resp.status_code == 201
    call_args = _mock_task.delay.call_args
    assert call_args[0][1] == "small"


@pytest.mark.asyncio
async def test_audio_upload_invalid_model(client: AsyncClient):
    """Invalid whisper model should return 400."""
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording", "whisper_model": "invalid_model"},
    )
    assert resp.status_code == 400
    assert "Invalid whisper model" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_image_upload_stays_completed(client: AsyncClient):
    """Non-audio uploads should have processing_status = completed (no transcription)."""
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("test.png", io.BytesIO(b"fake image"), "image/png")},
        data={"content_type": "other_media"},
    )
    assert resp.status_code == 201
    assert resp.json()["processing_status"] == "completed"


@pytest.mark.asyncio
async def test_get_transcript_not_found(client: AsyncClient):
    """Getting transcript for item without one should return 404."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/items/{item_id}/transcript")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_transcript_with_segments(client: AsyncClient, db_session: AsyncSession):
    """Getting transcript should return segments when available."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording"},
    )
    item_id = upload_resp.json()["id"]

    # Manually create transcript + segments in DB
    transcript = Transcript(
        media_item_id=uuid.UUID(item_id),
        full_text="Hello world this is a test",
        language="en",
    )
    db_session.add(transcript)
    await db_session.flush()

    for i, (start, end, text) in enumerate([
        (0.0, 2.5, "Hello world"),
        (2.5, 5.0, "this is a test"),
    ]):
        db_session.add(TranscriptSegment(
            transcript_id=transcript.id,
            start_time=start,
            end_time=end,
            text=text,
            segment_index=i,
        ))
    await db_session.commit()

    resp = await client.get(f"/api/items/{item_id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_text"] == "Hello world this is a test"
    assert data["language"] == "en"
    assert len(data["segments"]) == 2
    assert data["segments"][0]["text"] == "Hello world"
    assert data["segments"][0]["start_time"] == 0.0
    assert data["segments"][1]["text"] == "this is a test"


@pytest.mark.asyncio
async def test_retranscribe_audio_item(client: AsyncClient):
    """Re-transcribing should reset status and queue new task."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording"},
    )
    item_id = upload_resp.json()["id"]

    _reset_mock()
    resp = await client.post(f"/api/items/{item_id}/transcribe?whisper_model=small")

    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "pending"
    _mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_retranscribe_non_audio_fails(client: AsyncClient):
    """Retranscribing a non-audio item should return 400."""
    space_id = await _create_space(client)
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("test.png", io.BytesIO(b"fake image"), "image/png")},
        data={"content_type": "other_media"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.post(f"/api/items/{item_id}/transcribe")
    assert resp.status_code == 400
    assert "audio" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_transcription_status_endpoint(client: AsyncClient):
    """Transcription status endpoint should return item status."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/items/{item_id}/transcription-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == item_id
    assert data["processing_status"] == "pending"


@pytest.mark.asyncio
async def test_delete_item_with_transcript(client: AsyncClient, db_session: AsyncSession):
    """Deleting an item should cascade-delete its transcript."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_audio(),
        data={"content_type": "call_recording"},
    )
    item_id = upload_resp.json()["id"]

    # Create transcript
    transcript = Transcript(
        media_item_id=uuid.UUID(item_id),
        full_text="test transcript",
        language="en",
    )
    db_session.add(transcript)
    await db_session.commit()

    # Delete item
    del_resp = await client.delete(f"/api/items/{item_id}")
    assert del_resp.status_code == 204

    # Verify item is gone
    get_resp = await client.get(f"/api/items/{item_id}")
    assert get_resp.status_code == 404
