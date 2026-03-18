import io

import pytest
from httpx import AsyncClient


async def _create_space(client: AsyncClient) -> str:
    resp = await client.post("/api/spaces", json={"name": "Upload Test"})
    return resp.json()["id"]


def _make_file(name: str = "test.png", content: bytes = b"fake image data", content_type: str = "image/png"):
    return {"file": (name, io.BytesIO(content), content_type)}


@pytest.mark.asyncio
async def test_upload_file(client: AsyncClient):
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file(),
        data={"content_type": "other_media"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "test.png"
    assert data["mime_type"] == "image/png"
    assert data["space_id"] == space_id
    assert data["content_type"] == "other_media"
    assert data["file_url"].startswith("/api/files/")


@pytest.mark.asyncio
async def test_upload_with_timestamp(client: AsyncClient):
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file(),
        data={
            "content_type": "call_recording",
            "item_timestamp": "2026-03-15T10:30:00",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["item_timestamp"] is not None


@pytest.mark.asyncio
async def test_upload_invalid_type(client: AsyncClient):
    space_id = await _create_space(client)
    resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("test.txt", io.BytesIO(b"text"), "text/plain")},
        data={"content_type": "other_media"},
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_to_nonexistent_space(client: AsyncClient):
    resp = await client.post(
        "/api/spaces/00000000-0000-0000-0000-000000000000/upload",
        files=_make_file(),
        data={"content_type": "other_media"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_items(client: AsyncClient):
    space_id = await _create_space(client)
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("img1.png"),
        data={"content_type": "other_media"},
    )
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("img2.png"),
        data={"content_type": "chat_screenshot"},
    )

    resp = await client.get(f"/api/spaces/{space_id}/items")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_items_filter_by_type(client: AsyncClient):
    space_id = await _create_space(client)
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("call.mp3", b"audio", "audio/mpeg"),
        data={"content_type": "call_recording"},
    )
    await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("chat.png"),
        data={"content_type": "chat_screenshot"},
    )

    resp = await client.get(f"/api/spaces/{space_id}/items?content_type=call_recording")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["content_type"] == "call_recording"


@pytest.mark.asyncio
async def test_get_item(client: AsyncClient):
    space_id = await _create_space(client)
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file(),
        data={"content_type": "other_media"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id


@pytest.mark.asyncio
async def test_update_item_timestamp(client: AsyncClient):
    space_id = await _create_space(client)
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file(),
        data={"content_type": "other_media"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.put(f"/api/items/{item_id}", json={
        "item_timestamp": "2026-03-10T14:00:00Z",
        "timestamp_source": "user_provided",
    })
    assert resp.status_code == 200
    assert "2026-03-10" in resp.json()["item_timestamp"]


@pytest.mark.asyncio
async def test_update_item_content_type(client: AsyncClient):
    space_id = await _create_space(client)
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file(),
        data={"content_type": "other_media"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.put(f"/api/items/{item_id}", json={
        "content_type": "chat_screenshot",
    })
    assert resp.status_code == 200
    assert resp.json()["content_type"] == "chat_screenshot"


@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient):
    space_id = await _create_space(client)
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file(),
        data={"content_type": "other_media"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.delete(f"/api/items/{item_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/items/{item_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_serve_file(client: AsyncClient):
    space_id = await _create_space(client)
    content = b"fake image content for serving"
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files={"file": ("serve_test.png", io.BytesIO(content), "image/png")},
        data={"content_type": "other_media"},
    )
    item_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/files/{item_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == content


@pytest.mark.asyncio
async def test_full_upload_lifecycle(client: AsyncClient):
    # Create space
    space_id = await _create_space(client)

    # Upload
    upload_resp = await client.post(
        f"/api/spaces/{space_id}/upload",
        files=_make_file("lifecycle.png", b"lifecycle data"),
        data={
            "content_type": "chat_screenshot",
            "item_timestamp": "2026-03-15T10:00:00",
        },
    )
    assert upload_resp.status_code == 201
    item_id = upload_resp.json()["id"]

    # List
    list_resp = await client.get(f"/api/spaces/{space_id}/items")
    assert any(i["id"] == item_id for i in list_resp.json()["items"])

    # Update timestamp
    update_resp = await client.put(f"/api/items/{item_id}", json={
        "item_timestamp": "2026-03-14T08:00:00Z",
    })
    assert update_resp.status_code == 200

    # Serve file
    file_resp = await client.get(f"/api/files/{item_id}")
    assert file_resp.status_code == 200
    assert file_resp.content == b"lifecycle data"

    # Delete
    del_resp = await client.delete(f"/api/items/{item_id}")
    assert del_resp.status_code == 204

    # Verify gone
    gone_resp = await client.get(f"/api/items/{item_id}")
    assert gone_resp.status_code == 404
