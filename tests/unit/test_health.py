import pytest
from httpx import AsyncClient, ASGITransport

from src.api.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Patent Intelligence"
    assert "version" in data


@pytest.mark.asyncio
async def test_patent_stats_returns_structure(client: AsyncClient):
    response = await client.get("/api/patents/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_patents" in data
    assert "active" in data
    assert "expired" in data


@pytest.mark.asyncio
async def test_search_endpoint_validates_input(client: AsyncClient):
    response = await client.post("/api/search", json={"query": "battery technology"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "battery technology"
    assert data["search_type"] == "hybrid"
