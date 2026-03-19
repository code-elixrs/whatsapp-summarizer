import io
import sys
import uuid
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_item import MediaItem, ProcessingStatus


# Create mock stitch module so the lazy import in items.py works
_mock_stitch_module = ModuleType("app.tasks.stitch")
_mock_stitch_task = MagicMock()
_mock_stitch_task.delay.return_value = MagicMock(id="fake-stitch-task-id")
_mock_stitch_module.stitch_screenshots = _mock_stitch_task
sys.modules["app.tasks.stitch"] = _mock_stitch_module

# Ensure ocr mock is also present (items.py imports it too)
if "app.tasks.ocr" not in sys.modules:
    _mock_ocr_module = ModuleType("app.tasks.ocr")
    _mock_ocr_task = MagicMock()
    _mock_ocr_task.delay.return_value = MagicMock(id="fake-ocr-task-id")
    _mock_ocr_module.ocr_screenshot = _mock_ocr_task
    sys.modules["app.tasks.ocr"] = _mock_ocr_module


async def _create_space(client: AsyncClient) -> str:
    resp = await client.post("/api/spaces", json={"name": "Stitch Test"})
    return resp.json()["id"]


def _make_screenshot(name: str = "chat.png", content: bytes = b"fake image data"):
    return {"file": (name, io.BytesIO(content), "image/png")}


def _reset_mock():
    _mock_stitch_task.reset_mock()
    _mock_stitch_task.delay.return_value = MagicMock(id="fake-stitch-task-id")


async def _upload_screenshots(client: AsyncClient, space_id: str, count: int = 3, group_id: str | None = None):
    """Upload multiple screenshots, optionally with a shared group_id."""
    if group_id is None:
        group_id = str(uuid.uuid4())
    item_ids = []
    for i in range(count):
        resp = await client.post(
            f"/api/spaces/{space_id}/upload",
            files=_make_screenshot(f"chat_{i}.png", f"fake image {i}".encode()),
            data={
                "content_type": "chat_screenshot",
                "group_id": group_id,
                "group_order": str(i),
            },
        )
        assert resp.status_code == 201
        item_ids.append(resp.json()["id"])
    return item_ids, group_id


@pytest.mark.asyncio
async def test_create_group(client: AsyncClient):
    """Grouping items should assign a shared group_id and sequential order."""
    space_id = await _create_space(client)

    # Upload 3 ungrouped screenshots
    item_ids = []
    for i in range(3):
        resp = await client.post(
            f"/api/spaces/{space_id}/upload",
            files=_make_screenshot(f"shot_{i}.png"),
            data={"content_type": "chat_screenshot"},
        )
        item_ids.append(resp.json()["id"])

    resp = await client.post("/api/groups/create", json={"item_ids": item_ids})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3

    # All should share the same group_id
    group_ids = {item["group_id"] for item in data}
    assert len(group_ids) == 1
    assert data[0]["group_order"] == 0
    assert data[1]["group_order"] == 1
    assert data[2]["group_order"] == 2


@pytest.mark.asyncio
async def test_create_group_too_few_items(client: AsyncClient):
    """Creating a group with fewer than 2 items should fail."""
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={"content_type": "chat_screenshot"},
    )
    item_id = resp.json()["id"]

    resp = await client.post("/api/groups/create", json={"item_ids": [item_id]})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_group_items(client: AsyncClient):
    """Getting group items should return them in order."""
    space_id = await _create_space(client)
    item_ids, group_id = await _upload_screenshots(client, space_id, 3)

    resp = await client.get(f"/api/groups/{group_id}/items")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["group_order"] == 0
    assert data[1]["group_order"] == 1
    assert data[2]["group_order"] == 2


@pytest.mark.asyncio
async def test_get_group_items_not_found(client: AsyncClient):
    """Getting items for a non-existent group should return 404."""
    fake_group_id = str(uuid.uuid4())
    resp = await client.get(f"/api/groups/{fake_group_id}/items")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder_group(client: AsyncClient):
    """Reordering should update group_order and clear stitched_path."""
    space_id = await _create_space(client)
    item_ids, group_id = await _upload_screenshots(client, space_id, 3)

    # Reverse the order
    reversed_ids = list(reversed(item_ids))
    resp = await client.put(
        f"/api/groups/{group_id}/reorder",
        json={"item_ids": reversed_ids},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["id"] == reversed_ids[0]
    assert data[0]["group_order"] == 0
    assert data[2]["id"] == reversed_ids[2]
    assert data[2]["group_order"] == 2


@pytest.mark.asyncio
async def test_reorder_group_incomplete_ids(client: AsyncClient):
    """Reordering with missing item_ids should fail."""
    space_id = await _create_space(client)
    item_ids, group_id = await _upload_screenshots(client, space_id, 3)

    # Only pass 2 of 3 item_ids
    resp = await client.put(
        f"/api/groups/{group_id}/reorder",
        json={"item_ids": item_ids[:2]},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_stitch_group_triggers_task(client: AsyncClient):
    """Stitching a group should queue a Celery task."""
    _reset_mock()
    space_id = await _create_space(client)
    item_ids, group_id = await _upload_screenshots(client, space_id, 2)

    resp = await client.post(f"/api/groups/{group_id}/stitch")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["group_id"] == group_id
    assert data["items_count"] == 2
    _mock_stitch_task.delay.assert_called_once_with(group_id, True)


@pytest.mark.asyncio
async def test_stitch_group_auto_ocr_false(client: AsyncClient):
    """Stitching with auto_ocr=false should pass that to the task."""
    _reset_mock()
    space_id = await _create_space(client)
    _, group_id = await _upload_screenshots(client, space_id, 2)

    resp = await client.post(f"/api/groups/{group_id}/stitch?auto_ocr=false")
    assert resp.status_code == 200
    _mock_stitch_task.delay.assert_called_once_with(group_id, False)


@pytest.mark.asyncio
async def test_stitch_single_item_fails(client: AsyncClient):
    """Stitching a group with only 1 item should fail."""
    space_id = await _create_space(client)
    _, group_id = await _upload_screenshots(client, space_id, 1)

    resp = await client.post(f"/api/groups/{group_id}/stitch")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ungroup_items(client: AsyncClient):
    """Ungrouping should clear group_id, group_order, and stitched_path."""
    space_id = await _create_space(client)
    item_ids, group_id = await _upload_screenshots(client, space_id, 2)

    resp = await client.delete(f"/api/groups/{group_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items_affected"] == 2

    # Verify items are ungrouped
    for item_id in item_ids:
        resp = await client.get(f"/api/items/{item_id}")
        assert resp.json()["group_id"] is None
        assert resp.json()["group_order"] is None


@pytest.mark.asyncio
async def test_ungroup_not_found(client: AsyncClient):
    """Ungrouping a non-existent group should return 404."""
    fake_group_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/groups/{fake_group_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_with_group_id_preserves_group(client: AsyncClient):
    """Uploading with a group_id should store it on the item."""
    space_id = await _create_space(client)
    group_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_screenshot(),
        data={
            "content_type": "chat_screenshot",
            "group_id": group_id,
            "group_order": "0",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["group_id"] == group_id
    assert data["group_order"] == 0


@pytest.mark.asyncio
async def test_stitch_sets_items_to_pending(client: AsyncClient):
    """Triggering stitch should set all group items to pending status."""
    _reset_mock()
    space_id = await _create_space(client)
    item_ids, group_id = await _upload_screenshots(client, space_id, 2)

    await client.post(f"/api/groups/{group_id}/stitch")

    # Check each item is now pending
    for item_id in item_ids:
        resp = await client.get(f"/api/items/{item_id}")
        assert resp.json()["processing_status"] == "pending"
