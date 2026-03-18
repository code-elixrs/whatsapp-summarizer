import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_space(client: AsyncClient):
    response = await client.post("/api/spaces", json={
        "name": "Rahul Sharma",
        "description": "Test space",
        "color": "#3b82f6",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Rahul Sharma"
    assert data["description"] == "Test space"
    assert data["color"] == "#3b82f6"
    assert "id" in data
    assert data["item_counts"]["calls"] == 0


@pytest.mark.asyncio
async def test_create_space_minimal(client: AsyncClient):
    response = await client.post("/api/spaces", json={"name": "Priya"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Priya"
    assert data["color"] == "#7c3aed"  # default


@pytest.mark.asyncio
async def test_create_space_invalid_name(client: AsyncClient):
    response = await client.post("/api/spaces", json={"name": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_space_invalid_color(client: AsyncClient):
    response = await client.post("/api/spaces", json={
        "name": "Test",
        "color": "not-a-color",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_spaces(client: AsyncClient):
    await client.post("/api/spaces", json={"name": "Alice"})
    await client.post("/api/spaces", json={"name": "Bob"})

    response = await client.get("/api/spaces")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    names = [s["name"] for s in data["spaces"]]
    assert "Alice" in names
    assert "Bob" in names


@pytest.mark.asyncio
async def test_list_spaces_search(client: AsyncClient):
    await client.post("/api/spaces", json={"name": "Unique Name XYZ"})

    response = await client.get("/api/spaces?search=Unique")
    assert response.status_code == 200
    data = response.json()
    assert any(s["name"] == "Unique Name XYZ" for s in data["spaces"])

    response = await client.get("/api/spaces?search=nonexistent999")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_space(client: AsyncClient):
    create_resp = await client.post("/api/spaces", json={"name": "Get Test"})
    space_id = create_resp.json()["id"]

    response = await client.get(f"/api/spaces/{space_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test"


@pytest.mark.asyncio
async def test_get_space_not_found(client: AsyncClient):
    response = await client.get("/api/spaces/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_space(client: AsyncClient):
    create_resp = await client.post("/api/spaces", json={"name": "Before Update"})
    space_id = create_resp.json()["id"]

    response = await client.put(f"/api/spaces/{space_id}", json={
        "name": "After Update",
        "color": "#ef4444",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "After Update"
    assert data["color"] == "#ef4444"


@pytest.mark.asyncio
async def test_update_space_partial(client: AsyncClient):
    create_resp = await client.post("/api/spaces", json={
        "name": "Partial",
        "description": "Original desc",
    })
    space_id = create_resp.json()["id"]

    response = await client.put(f"/api/spaces/{space_id}", json={
        "name": "Partial Updated",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Partial Updated"
    # description should remain since it was not in the update
    assert data["description"] == "Original desc"


@pytest.mark.asyncio
async def test_update_space_not_found(client: AsyncClient):
    response = await client.put(
        "/api/spaces/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_space(client: AsyncClient):
    create_resp = await client.post("/api/spaces", json={"name": "To Delete"})
    space_id = create_resp.json()["id"]

    response = await client.delete(f"/api/spaces/{space_id}")
    assert response.status_code == 204

    get_resp = await client.get(f"/api/spaces/{space_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_space_not_found(client: AsyncClient):
    response = await client.delete("/api/spaces/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_full_crud_flow(client: AsyncClient):
    # Create
    create_resp = await client.post("/api/spaces", json={
        "name": "CRUD Flow",
        "description": "Full flow test",
        "color": "#10b981",
    })
    assert create_resp.status_code == 201
    space_id = create_resp.json()["id"]

    # Read
    get_resp = await client.get(f"/api/spaces/{space_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "CRUD Flow"

    # List
    list_resp = await client.get("/api/spaces")
    assert any(s["id"] == space_id for s in list_resp.json()["spaces"])

    # Update
    update_resp = await client.put(f"/api/spaces/{space_id}", json={
        "name": "CRUD Updated",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "CRUD Updated"

    # Delete
    delete_resp = await client.delete(f"/api/spaces/{space_id}")
    assert delete_resp.status_code == 204

    # Verify gone
    gone_resp = await client.get(f"/api/spaces/{space_id}")
    assert gone_resp.status_code == 404
