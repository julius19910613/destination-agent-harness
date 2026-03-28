"""API endpoint tests with Harness."""
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_extract_destination_endpoint_with_cache():
    """Test extract destination endpoint (should use cache on second call)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First call
        response1 = await client.post(
            "/api/extract-destination",
            json={"text": "我想去巴黎旅游"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["destination"] == "巴黎"

        # Second call (should be faster due to cache)
        response2 = await client.post(
            "/api/extract-destination",
            json={"text": "我想去巴黎旅游"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2 == data1  # Should return same result from cache


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
