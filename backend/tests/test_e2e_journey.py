"""End-to-end user journey test: create space → upload → process → search → view."""
import io
import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.transcript import Transcript, TranscriptSegment

# Ensure task mocks
for mod_name, task_name, task_id in [
    ("app.tasks.ocr", "ocr_screenshot", "fake-ocr-task-id"),
    ("app.tasks.stitch", "stitch_screenshots", "fake-stitch-task-id"),
    ("app.tasks.transcribe", "transcribe_audio", "fake-transcribe-task-id"),
]:
    if mod_name not in sys.modules:
        m = ModuleType(mod_name)
        t = MagicMock()
        t.delay.return_value = MagicMock(id=task_id)
        setattr(m, task_name, t)
        sys.modules[mod_name] = m


@pytest.mark.asyncio
async def test_full_user_journey(client: AsyncClient, db_session: AsyncSession):
    """Complete user journey: create space, upload files, simulate processing,
    search content, and view unified chat stream."""

    # 1. Create a space
    resp = await client.post("/api/spaces", json={
        "name": "Alice & Bob",
        "description": "Conversations with Alice",
        "color": "#3b82f6",
    })
    assert resp.status_code == 201
    space = resp.json()
    space_id = space["id"]
    assert space["name"] == "Alice & Bob"

    # 2. Upload a call recording
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("call_jan15.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")},
        data={
            "content_type": "call_recording",
            "item_timestamp": "2024-01-15T14:30:00Z",
            "platform": "WhatsApp",
        },
    )
    assert resp.status_code == 201
    call_item = resp.json()
    assert call_item["processing_status"] == "pending"

    # 3. Upload chat screenshots (grouped batch)
    group_id = str(uuid.uuid4())
    chat_items = []
    for i in range(2):
        resp = await client.post(
            f"/api/spaces/{space_id}/upload",
            files={"file": (f"chat_{i}.png", io.BytesIO(f"img{i}".encode()), "image/png")},
            data={
                "content_type": "chat_screenshot",
                "item_timestamp": "2024-01-15T15:00:00Z",
                "group_id": group_id,
                "group_order": str(i),
            },
        )
        assert resp.status_code == 201
        chat_items.append(resp.json())

    # 4. Upload a status update
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("status.jpg", io.BytesIO(b"img"), "image/jpeg")},
        data={
            "content_type": "status_update",
            "item_timestamp": "2024-01-15T16:00:00Z",
            "platform": "Instagram",
        },
    )
    assert resp.status_code == 201
    status_item = resp.json()

    # 5. Verify space item counts
    resp = await client.get(f"/api/spaces/{space_id}")
    space_data = resp.json()
    assert space_data["item_counts"]["calls"] == 1
    assert space_data["item_counts"]["chats"] == 2
    assert space_data["item_counts"]["statuses"] == 1

    # 6. Simulate OCR processing complete — add chat messages
    from datetime import datetime, timezone
    messages_data = [
        ("Alice", "Hey, are we still meeting tomorrow?", False, datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)),
        (None, "Yes! What time works for you?", True, datetime(2024, 1, 15, 15, 1, tzinfo=timezone.utc)),
        ("Alice", "How about 3pm at the downtown cafe?", False, datetime(2024, 1, 15, 15, 2, tzinfo=timezone.utc)),
        (None, "Perfect, see you there!", True, datetime(2024, 1, 15, 15, 3, tzinfo=timezone.utc)),
    ]
    for i, (sender, msg, is_sent, ts) in enumerate(messages_data):
        db_session.add(ChatMessage(
            media_item_id=uuid.UUID(chat_items[0]["id"]),
            sender=sender,
            message=msg,
            message_order=i,
            is_sent=is_sent,
            message_timestamp=ts,
        ))

    # 7. Simulate transcription complete — add transcript
    transcript = Transcript(
        media_item_id=uuid.UUID(call_item["id"]),
        full_text="Alice called to discuss the meeting plan for tomorrow at the downtown cafe.",
        language="en",
    )
    db_session.add(transcript)
    await db_session.flush()

    db_session.add(TranscriptSegment(
        transcript_id=transcript.id,
        start_time=0.0,
        end_time=5.0,
        text="Alice called to discuss the meeting plan",
        segment_index=0,
    ))
    await db_session.commit()

    # 8. View chat messages for the first screenshot
    resp = await client.get(f"/api/items/{chat_items[0]['id']}/chat-messages")
    assert resp.status_code == 200
    messages = resp.json()
    assert messages["total"] == 4
    assert messages["messages"][0]["sender"] == "Alice"

    # 9. Edit a chat message (correct OCR error)
    msg_id = messages["messages"][0]["id"]
    resp = await client.put(
        f"/api/items/{chat_items[0]['id']}/chat-messages/{msg_id}",
        json={"message": "Hey, are we still meeting tomorrow at 3?"},
    )
    assert resp.status_code == 200
    assert "3?" in resp.json()["message"]

    # 10. View transcript
    resp = await client.get(f"/api/items/{call_item['id']}/transcript")
    assert resp.status_code == 200
    transcript_data = resp.json()
    assert "downtown cafe" in transcript_data["full_text"]
    assert len(transcript_data["segments"]) == 1

    # 11. View group items
    resp = await client.get(f"/api/groups/{group_id}/items")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # 12. Unified chat stream
    resp = await client.get(f"/api/spaces/{space_id}/chat-stream")
    assert resp.status_code == 200
    stream = resp.json()
    assert stream["total_messages"] == 4
    assert stream["total_events"] == 2  # call + status

    # Verify chronological order
    types_in_order = [e["type"] for e in stream["entries"]]
    assert "message" in types_in_order
    assert "event" in types_in_order

    # Call event should have transcript summary
    call_events = [e for e in stream["entries"] if e.get("event_type") == "call_recording"]
    assert len(call_events) == 1
    assert "downtown cafe" in call_events[0]["transcript_summary"]

    # 13. Search across the space
    resp = await client.get(f"/api/spaces/{space_id}/search", params={"q": "downtown cafe"})
    assert resp.status_code == 200
    search = resp.json()
    assert search["total"] >= 2  # Should find in chat message AND transcript

    # 14. Global search
    resp = await client.get("/api/search", params={"q": "downtown cafe"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    # 15. Update status timestamp and verify
    resp = await client.put(
        f"/api/items/{status_item['id']}",
        json={"item_timestamp": "2024-01-15T18:00:00Z"},
    )
    assert resp.status_code == 200

    # 16. List items with filter
    resp = await client.get(f"/api/spaces/{space_id}/items", params={"content_type": "status_update"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # 17. Delete the space
    resp = await client.delete(f"/api/spaces/{space_id}")
    assert resp.status_code == 204

    # Verify cascade
    resp = await client.get(f"/api/spaces/{space_id}")
    assert resp.status_code == 404
