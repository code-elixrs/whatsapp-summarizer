import io
import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.transcript import Transcript

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


async def _create_space(client: AsyncClient, name: str = "Search Test") -> str:
    resp = await client.post("/api/spaces", json={"name": name})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_global_search_empty(client: AsyncClient):
    """Global search with no matching content returns empty."""
    resp = await client.get("/api/search", params={"q": "xyznonexistent"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["total"] == 0
    assert data["query"] == "xyznonexistent"


@pytest.mark.asyncio
async def test_global_search_chat_messages(client: AsyncClient, db_session: AsyncSession):
    """Global search should find chat messages by content."""
    space_id = await _create_space(client)

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("chat.png", io.BytesIO(b"img"), "image/png")},
        data={"content_type": "chat_screenshot"},
    )
    item_id = resp.json()["id"]

    db_session.add(ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Alice",
        message="Meeting tomorrow at the Riverside Cafe downtown",
        message_order=0,
        is_sent=False,
    ))
    await db_session.commit()

    resp = await client.get("/api/search", params={"q": "Riverside Cafe"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["result_type"] == "chat_message" for r in data["results"])


@pytest.mark.asyncio
async def test_global_search_transcripts(client: AsyncClient, db_session: AsyncSession):
    """Global search should find transcripts by content."""
    space_id = await _create_space(client)

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("call.mp3", io.BytesIO(b"audio"), "audio/mpeg")},
        data={"content_type": "call_recording"},
    )
    item_id = resp.json()["id"]

    db_session.add(Transcript(
        media_item_id=uuid.UUID(item_id),
        full_text="We discussed the quarterly budget allocation and hiring plans for Q2",
    ))
    await db_session.commit()

    resp = await client.get("/api/search", params={"q": "budget allocation"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["result_type"] == "transcript" for r in data["results"])


@pytest.mark.asyncio
async def test_global_search_media_items(client: AsyncClient):
    """Global search should find media items by title/notes/filename."""
    space_id = await _create_space(client)

    await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("vacation_photos_beach.jpg", io.BytesIO(b"img"), "image/jpeg")},
        data={"content_type": "other_media", "title": "Summer vacation beach photos"},
    )

    resp = await client.get("/api/search", params={"q": "vacation beach"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["result_type"] == "media_item" for r in data["results"])


@pytest.mark.asyncio
async def test_space_search(client: AsyncClient, db_session: AsyncSession):
    """In-space search should only return results from that space."""
    space1_id = await _create_space(client, "Space One")
    space2_id = await _create_space(client, "Space Two")

    # Add content to both spaces
    for sid, msg in [(space1_id, "Unique kittens content"), (space2_id, "Unique puppies content")]:
        resp = await client.post(
            f"/api/spaces/{sid}/upload",
            files={"file": ("chat.png", io.BytesIO(b"img"), "image/png")},
            data={"content_type": "chat_screenshot"},
        )
        item_id = resp.json()["id"]
        db_session.add(ChatMessage(
            media_item_id=uuid.UUID(item_id),
            sender="Bob",
            message=msg,
            message_order=0,
            is_sent=False,
        ))
    await db_session.commit()

    # Search in space1 for "puppies" should return nothing
    resp = await client.get(f"/api/spaces/{space1_id}/search", params={"q": "puppies"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # Search in space2 for "puppies" should find it
    resp = await client.get(f"/api/spaces/{space2_id}/search", params={"q": "puppies"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_space_search_with_type_filter(client: AsyncClient, db_session: AsyncSession):
    """In-space search should filter by content type."""
    space_id = await _create_space(client)

    # Chat screenshot with searchable content
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("chat.png", io.BytesIO(b"img"), "image/png")},
        data={"content_type": "chat_screenshot"},
    )
    item_id = resp.json()["id"]
    db_session.add(ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Charlie",
        message="Important meeting schedule for the project review",
        message_order=0,
        is_sent=False,
    ))
    await db_session.commit()

    # Search with matching type
    resp = await client.get(
        f"/api/spaces/{space_id}/search",
        params={"q": "meeting schedule", "content_type": "chat_screenshot"},
    )
    assert resp.json()["total"] >= 1

    # Search with non-matching type
    resp = await client.get(
        f"/api/spaces/{space_id}/search",
        params={"q": "meeting schedule", "content_type": "call_recording"},
    )
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_query_too_short(client: AsyncClient):
    """Search query must be at least 1 character."""
    resp = await client.get("/api/search", params={"q": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_space_search_not_found(client: AsyncClient):
    """Searching in a non-existent space should return 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/spaces/{fake_id}/search", params={"q": "test"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_results_include_space_name(client: AsyncClient, db_session: AsyncSession):
    """Search results should include the space name."""
    space_id = await _create_space(client, "My Test Space")

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("chat.png", io.BytesIO(b"img"), "image/png")},
        data={"content_type": "chat_screenshot"},
    )
    item_id = resp.json()["id"]
    db_session.add(ChatMessage(
        media_item_id=uuid.UUID(item_id),
        sender="Dan",
        message="Searchable elephant content for testing global results",
        message_order=0,
        is_sent=False,
    ))
    await db_session.commit()

    resp = await client.get("/api/search", params={"q": "elephant"})
    data = resp.json()
    assert data["total"] >= 1
    assert data["results"][0]["space_name"] == "My Test Space"
