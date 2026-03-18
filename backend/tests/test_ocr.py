import io
import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.media_item import MediaItem, ProcessingStatus


# Create a mock ocr module so the lazy import in items.py works
_mock_ocr_module = ModuleType("app.tasks.ocr")
_mock_task = MagicMock()
_mock_task.delay.return_value = MagicMock(id="fake-ocr-task-id")
_mock_ocr_module.ocr_screenshot = _mock_task
sys.modules["app.tasks.ocr"] = _mock_ocr_module


async def _create_space(client: AsyncClient) -> str:
    resp = await client.post("/api/spaces", json={"name": "OCR Test"})
    return resp.json()["id"]


def _make_screenshot(name: str = "chat.png", content: bytes = b"fake image data"):
    return {"file": (name, io.BytesIO(content), "image/png")}


def _reset_mock():
    _mock_task.reset_mock()
    _mock_task.delay.return_value = MagicMock(id="fake-ocr-task-id")


@pytest.mark.asyncio
async def test_chat_screenshot_upload_triggers_ocr(client: AsyncClient):
    """Uploading a chat screenshot should set pending status and queue OCR."""
    _reset_mock()
    space_id = await _create_space(client)

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["processing_status"] == "pending"
    assert data["content_type"] == "chat_screenshot"
    _mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_non_chat_image_stays_completed(client: AsyncClient):
    """Non-chat-screenshot images should have processing_status = completed."""
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "other_media"},
    )
    assert resp.status_code == 201
    assert resp.json()["processing_status"] == "completed"


@pytest.mark.asyncio
async def test_get_chat_messages_empty(client: AsyncClient):
    """Getting chat messages for item with no messages should return empty list."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/items/{item_id}/chat-messages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["messages"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_chat_messages_with_data(client: AsyncClient, db_session: AsyncSession):
    """Getting chat messages should return stored messages in order."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    # Manually create chat messages in DB
    for i, (sender, msg, is_sent) in enumerate([
        ("Alice", "Hey, how are you?", False),
        (None, "I'm good, thanks!", True),
        ("Alice", "Want to grab coffee?", False),
    ]):
        db_session.add(ChatMessage(
            media_item_id=uuid.UUID(item_id),
            sender=sender,
            message=msg,
            message_order=i,
            is_sent=is_sent,
        ))
    await db_session.commit()

    resp = await client.get(f"/api/items/{item_id}/chat-messages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["messages"][0]["sender"] == "Alice"
    assert data["messages"][0]["message"] == "Hey, how are you?"
    assert data["messages"][0]["is_sent"] is False
    assert data["messages"][1]["is_sent"] is True
    assert data["messages"][2]["message"] == "Want to grab coffee?"


@pytest.mark.asyncio
async def test_update_chat_message(client: AsyncClient, db_session: AsyncSession):
    """Editing a chat message should update the message text."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    msg = ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Alice",
        message="Helo world",  # OCR error
        message_order=0,
        is_sent=False,
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    resp = await client.put(
        f"/api/items/{item_id}/chat-messages/{msg.id}",
        json={"message": "Hello world", "sender": "Bob"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Hello world"
    assert data["sender"] == "Bob"


@pytest.mark.asyncio
async def test_update_chat_message_not_found(client: AsyncClient):
    """Updating a non-existent chat message should return 404."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    fake_msg_id = str(uuid.uuid4())
    resp = await client.put(
        f"/api/items/{item_id}/chat-messages/{fake_msg_id}",
        json={"message": "test"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rerun_ocr(client: AsyncClient):
    """Re-running OCR should reset status and queue new task."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    _reset_mock()
    resp = await client.post(f"/api/items/{item_id}/ocr")
    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "pending"
    _mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_rerun_ocr_non_image_fails(client: AsyncClient):
    """Re-running OCR on a non-image item should return 400."""
    _reset_mock()
    space_id = await _create_space(client)

    # Upload audio file
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("test.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
        data={"content_type": "call_recording"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.post(f"/api/items/{item_id}/ocr")
    assert resp.status_code == 400
    assert "image" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_item_cascades_chat_messages(client: AsyncClient, db_session: AsyncSession):
    """Deleting an item should cascade-delete its chat messages."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    db_session.add(ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Alice",
        message="test message",
        message_order=0,
        is_sent=False,
    ))
    await db_session.commit()

    del_resp = await client.delete(f"/api/items/{item_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/items/{item_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_processing_status_endpoint_for_screenshot(client: AsyncClient):
    """Processing status endpoint should work for screenshot items."""
    _reset_mock()
    space_id = await _create_space(client)

    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/items/{item_id}/transcription-status")
    assert resp.status_code == 200
    assert resp.json()["processing_status"] == "pending"
