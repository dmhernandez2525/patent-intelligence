from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
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
async def test_patent_stats_returns_structure():
    """Test patent stats endpoint returns correct structure with mocked DB."""
    from src.api.routes.patents import patent_stats

    # Create a mock session
    mock_session = AsyncMock()

    # Mock the execute method to return mock scalars for each query
    mock_result = MagicMock()
    mock_result.scalar.return_value = 10  # Return 10 for all count queries

    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call the endpoint directly with mocked session
    result = await patent_stats(session=mock_session)

    assert "total_patents" in result
    assert "active" in result
    assert "expired" in result
    assert "lapsed" in result
    assert "countries" in result
    assert result["total_patents"] == 10


@pytest.mark.asyncio
async def test_search_endpoint_validates_input():
    """Test search endpoint returns correct structure with mocked service."""
    from src.api.routes.search import search_patents
    from src.api.schemas.search import SearchRequest

    # Create mock session and search service
    mock_session = AsyncMock()

    with patch("src.api.routes.search.search_service") as mock_search_service:
        mock_search_service.hybrid_search = AsyncMock(
            return_value=([], 0)  # Returns (results, total)
        )

        request = SearchRequest(query="battery technology")
        result = await search_patents(request=request, session=mock_session)

        assert result.query == "battery technology"
        assert result.search_type == "hybrid"
