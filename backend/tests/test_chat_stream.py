import io
import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.media_item import MediaItem, ProcessingStatus, ContentType
from app.models.transcript import Transcript

# Ensure task mocks are in place
if "app.tasks.ocr" not in sys.modules:
    _m = ModuleType("app.tasks.ocr")
    _t = MagicMock()
    _t.delay.return_value = MagicMock(id="fake-ocr-task-id")
    _m.ocr_screenshot = _t
    sys.modules["app.tasks.ocr"] = _m

if "app.tasks.stitch" not in sys.modules:
    _m = ModuleType("app.tasks.stitch")
    _t = MagicMock()
    _t.delay.return_value = MagicMock(id="fake-stitch-task-id")
    _m.stitch_screenshots = _t
    sys.modules["app.tasks.stitch"] = _m

if "app.tasks.transcribe" not in sys.modules:
    _m = ModuleType("app.tasks.transcribe")
    _t = MagicMock()
    _t.delay.return_value = MagicMock(id="fake-transcribe-task-id")
    _m.transcribe_audio = _t
    sys.modules["app.tasks.transcribe"] = _m


async def _create_space(client: AsyncClient) -> str:
    resp = await client.post("/api/spaces", json={"name": "Stream Test"})
    return resp.json()["id"]


def _make_file(name: str, content: bytes, mime: str):
    return {"file": (name, io.BytesIO(content), mime)}


@pytest.mark.asyncio
async def test_chat_stream_empty(client: AsyncClient):
    """Chat stream for a space with no items should return empty."""
    space_id = await _create_space(client)
    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entries"] == []
    assert data["total_messages"] == 0
    assert data["total_events"] == 0


@pytest.mark.asyncio
async def test_chat_stream_messages_only(client: AsyncClient, db_session: AsyncSession):
    """Chat stream should include chat messages from screenshots."""
    space_id = await _create_space(client)

    # Upload a chat screenshot
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("chat.png", b"img", "image/png"),
        data={"content_type": "chat_screenshot"},
    )
    item_id = resp.json()["id"]

    # Add chat messages
    from datetime import datetime, timezone
    for i, (sender, msg, is_sent) in enumerate([
        ("Alice", "Hello!", False),
        (None, "Hi Alice!", True),
    ]):
        db_session.add(ChatMessage(
            media_item_id=uuid.UUID(item_id),
            sender=sender,
            message=msg,
            message_order=i,
            is_sent=is_sent,
            message_timestamp=datetime(2024, 1, 1, 10, i, tzinfo=timezone.utc),
        ))
    await db_session.commit()

    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] == 2
    assert data["total_events"] == 0
    assert data["entries"][0]["type"] == "message"
    assert data["entries"][0]["sender"] == "Alice"
    assert data["entries"][0]["message"] == "Hello!"
    assert data["entries"][0]["is_sent"] is False
    assert data["entries"][1]["is_sent"] is True


@pytest.mark.asyncio
async def test_chat_stream_events_only(client: AsyncClient):
    """Chat stream should include non-chat items as events."""
    space_id = await _create_space(client)

    # Upload a call recording
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("call.mp3", b"audio", "audio/mpeg"),
        data={"content_type": "call_recording", "platform": "WhatsApp"},
    )

    # Upload a status update
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("status.jpg", b"img", "image/jpeg"),
        data={"content_type": "status_update", "platform": "Instagram"},
    )

    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] == 0
    assert data["total_events"] == 2

    event_types = {e["event_type"] for e in data["entries"]}
    assert "call_recording" in event_types
    assert "status_update" in event_types

    # Check platform is included
    platforms = {e["platform"] for e in data["entries"]}
    assert "WhatsApp" in platforms
    assert "Instagram" in platforms


@pytest.mark.asyncio
async def test_chat_stream_mixed(client: AsyncClient, db_session: AsyncSession):
    """Chat stream should merge messages and events in chronological order."""
    space_id = await _create_space(client)
    from datetime import datetime, timezone

    # Upload a chat screenshot with a timestamp
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("chat.png", b"img", "image/png"),
        data={
            "content_type": "chat_screenshot",
            "item_timestamp": "2024-01-01T10:00:00Z",
        },
    )
    item_id = resp.json()["id"]

    # Add a message
    db_session.add(ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Bob",
        message="Hey",
        message_order=0,
        is_sent=False,
        message_timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
    ))
    await db_session.commit()

    # Upload a call recording with a later timestamp
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("call.mp3", b"audio", "audio/mpeg"),
        data={
            "content_type": "call_recording",
            "item_timestamp": "2024-01-01T11:00:00Z",
        },
    )

    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] == 1
    assert data["total_events"] == 1

    # Message should come before event (10:00 < 11:00)
    assert data["entries"][0]["type"] == "message"
    assert data["entries"][1]["type"] == "event"


@pytest.mark.asyncio
async def test_chat_stream_with_transcript_summary(client: AsyncClient, db_session: AsyncSession):
    """Chat stream events for calls should include transcript summary."""
    space_id = await _create_space(client)

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("call.mp3", b"audio", "audio/mpeg"),
        data={"content_type": "call_recording"},
    )
    item_id = resp.json()["id"]

    # Add transcript
    transcript = Transcript(
        media_item_id=uuid.UUID(item_id),
        full_text="This is a test transcript that should appear as a summary in the chat stream.",
    )
    db_session.add(transcript)
    await db_session.commit()

    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    assert resp.status_code == 200
    data = resp.json()
    call_event = next(e for e in data["entries"] if e["event_type"] == "call_recording")
    assert call_event["transcript_summary"] is not None
    assert "test transcript" in call_event["transcript_summary"]


@pytest.mark.asyncio
async def test_chat_stream_source_tracking(client: AsyncClient, db_session: AsyncSession):
    """Chat stream messages should include source_item_id and source_group_id."""
    space_id = await _create_space(client)
    group_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("chat.png", b"img", "image/png"),
        data={
            "content_type": "chat_screenshot",
            "group_id": group_id,
            "group_order": "0",
        },
    )
    item_id = resp.json()["id"]

    db_session.add(ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Alice",
        message="Test",
        message_order=0,
        is_sent=False,
    ))
    await db_session.commit()

    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    data = resp.json()
    msg = data["entries"][0]
    assert msg["source_item_id"] == item_id
    assert msg["source_group_id"] == group_id


@pytest.mark.asyncio
async def test_chat_stream_not_found(client: AsyncClient):
    """Chat stream for non-existent space should return 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/spaces/{fake_id}/chat-stream")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_status_timestamp_update_reorders(client: AsyncClient):
    """Updating a status item's timestamp should be reflected on re-fetch."""
    space_id = await _create_space(client)

    # Upload two statuses
    r1 = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("s1.jpg", b"img1", "image/jpeg"),
        data={
            "content_type": "status_update",
            "item_timestamp": "2024-01-01T10:00:00Z",
        },
    )
    r2 = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("s2.jpg", b"img2", "image/jpeg"),
        data={
            "content_type": "status_update",
            "item_timestamp": "2024-01-01T12:00:00Z",
        },
    )
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Verify initial order in stream
    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    events = resp.json()["entries"]
    assert events[0]["item_id"] == id1  # 10:00
    assert events[1]["item_id"] == id2  # 12:00

    # Update id1's timestamp to be after id2
    await client.put(
        f"/api/items/{id1}",
        json={"item_timestamp": "2024-01-01T14:00:00Z", "timestamp_source": "user_provided"},
    )

    # Verify new order
    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    events = resp.json()["entries"]
    assert events[0]["item_id"] == id2  # 12:00
    assert events[1]["item_id"] == id1  # 14:00 (updated)
