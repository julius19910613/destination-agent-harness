"""Harness functionality tests."""
import pytest
from app.agent.destination_extractor import get_destination_extractor
from app.agent.tools.language_detector import LanguageDetectorTool
from app.agent.tools.cache_manager import CacheManager


@pytest.mark.asyncio
async def test_language_detection():
    """Test language detection tool."""
    detector = LanguageDetectorTool()

    # Test Chinese
    result = await detector.execute("我想去巴黎")
    assert result["language"] == "zh"
    assert result["confidence"] > 0

    # Test English
    result = await detector.execute("I want to go to Paris")
    assert result["language"] == "en"
    assert result["confidence"] > 0

    # Test Japanese
    result = await detector.execute("東京に行きたい")
    assert result["language"] == "ja"
    assert result["confidence"] > 0


@pytest.mark.asyncio
async def test_cache():
    """Test cache manager."""
    cache = CacheManager(ttl=60)

    # Test cache set and get
    test_data = {"destination": "Paris", "country": "France"}
    await cache.set("test text", test_data)

    cached = await cache.get("test text")
    assert cached == test_data

    # Test cache miss
    not_cached = await cache.get("nonexistent")
    assert not_cached is None

    # Test cache stats
    stats = cache.get_stats()
    assert stats["total_items"] == 1
    assert stats["ttl"] == 60


@pytest.mark.asyncio
async def test_extract_with_harness():
    """Test extraction with Harness (language detection + cache)."""
    extractor = get_destination_extractor()

    # First call (no cache)
    result1 = await extractor.extract_destination("我想去巴黎旅游")
    assert result1.destination == "巴黎"
    assert result1.country == "法国"
    assert result1.confidence > 0

    # Second call (with cache)
    result2 = await extractor.extract_destination("我想去巴黎旅游")
    assert result2.destination == "巴黎"
    assert result2 == result1  # Should be exactly the same (from cache)


@pytest.mark.asyncio
async def test_batch_extract_with_harness():
    """Test batch extraction with Harness."""
    extractor = get_destination_extractor()

    texts = ["想去巴黎", "计划去东京", "考虑纽约留学"]
    results = await extractor.batch_extract_destinations(texts)

    assert len(results) == 3
    assert results[0].destination == "巴黎"
    assert results[1].destination == "东京"
    assert results[2].destination == "纽约"


@pytest.mark.asyncio
async def test_multilingual_extraction():
    """Test extraction in different languages."""
    extractor = get_destination_extractor()

    # Chinese
    result_zh = await extractor.extract_destination("我想去巴黎")
    assert result_zh.destination == "巴黎"

    # English
    result_en = await extractor.extract_destination("I want to visit Paris")
    assert result_en.destination == "Paris"

    # Japanese
    result_ja = await extractor.extract_destination("東京に行きたい")
    assert result_ja.destination == "東京"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
