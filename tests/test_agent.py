"""Tests for the destination extraction agent."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.agent.gemini_client import GeminiClient
from app.agent.destination_extractor import DestinationExtractor
from app.models.schemas import DestinationExtractionResponse


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client."""
    client = Mock(spec=GeminiClient)
    client.api_key = "test_api_key"
    client.model = "gemini-2.0-flash-exp"
    return client


@pytest.fixture
def destination_extractor(mock_gemini_client):
    """Create a DestinationExtractor with mocked client."""
    extractor = DestinationExtractor(client=mock_gemini_client)
    return extractor


class TestDestinationExtractor:
    """Test cases for DestinationExtractor."""

    @pytest.mark.asyncio
    async def test_extract_destination_success(self, destination_extractor, mock_gemini_client):
        """Test successful destination extraction."""
        # Mock the client response
        mock_response = Mock()
        mock_response.text = '{"destination": "巴黎", "country": "法国", "confidence": 0.95}'
        mock_gemini_client.generate_json = AsyncMock(return_value=mock_response.text)

        result = await destination_extractor.extract_destination("我想去巴黎旅游")

        assert isinstance(result, DestinationExtractionResponse)
        assert result.destination == "巴黎"
        assert result.country == "法国"
        assert result.confidence == 0.95
        assert result.raw_text == "我想去巴黎旅游"
        mock_gemini_client.generate_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_destination_with_markdown(self, destination_extractor, mock_gemini_client):
        """Test destination extraction with markdown code blocks in response."""
        mock_gemini_client.generate_json = AsyncMock(
            return_value='```json\n{"destination": "东京", "country": "日本", "confidence": 0.9}\n```'
        )

        result = await destination_extractor.extract_destination("计划去东京旅行")

        assert result.destination == "东京"
        assert result.country == "日本"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_extract_destination_empty_text(self, destination_extractor):
        """Test extraction with empty text raises ValueError."""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await destination_extractor.extract_destination("")

    @pytest.mark.asyncio
    async def test_extract_destination_whitespace_only(self, destination_extractor):
        """Test extraction with whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            await destination_extractor.extract_destination("   ")

    @pytest.mark.asyncio
    async def test_extract_destination_invalid_json(self, destination_extractor, mock_gemini_client):
        """Test extraction with invalid JSON response."""
        mock_gemini_client.generate_json = AsyncMock(return_value="not valid json")

        with pytest.raises(ValueError, match="Invalid JSON response"):
            await destination_extractor.extract_destination("test text")

    @pytest.mark.asyncio
    async def test_extract_destination_api_error(self, destination_extractor, mock_gemini_client):
        """Test extraction when API call fails."""
        mock_gemini_client.generate_json = AsyncMock(side_effect=Exception("API error"))

        with pytest.raises(Exception, match="API error"):
            await destination_extractor.extract_destination("测试文本")

    @pytest.mark.asyncio
    async def test_batch_extract_destinations(self, destination_extractor, mock_gemini_client):
        """Test batch destination extraction."""
        mock_gemini_client.generate_json = AsyncMock(
            side_effect=[
                '{"destination": "巴黎", "country": "法国", "confidence": 0.95}',
                '{"destination": "东京", "country": "日本", "confidence": 0.9}',
                '{"destination": "纽约", "country": "美国", "confidence": 0.88}',
            ]
        )

        texts = ["我想去巴黎", "计划去东京", "想去纽约看看"]
        results = await destination_extractor.batch_extract_destinations(texts)

        assert len(results) == 3
        assert results[0].destination == "巴黎"
        assert results[1].destination == "东京"
        assert results[2].destination == "纽约"

    @pytest.mark.asyncio
    async def test_batch_extract_empty_list(self, destination_extractor):
        """Test batch extraction with empty list."""
        with pytest.raises(ValueError, match="Cannot extract from empty text list"):
            await destination_extractor.batch_extract_destinations([])

    @pytest.mark.asyncio
    async def test_batch_extract_with_partial_failure(self, destination_extractor, mock_gemini_client):
        """Test batch extraction when some extractions fail."""
        mock_gemini_client.generate_json = AsyncMock(
            side_effect=[
                '{"destination": "巴黎", "country": "法国", "confidence": 0.95}',
                Exception("API error"),
                '{"destination": "纽约", "country": "美国", "confidence": 0.88}',
            ]
        )

        texts = ["我想去巴黎", "失败的请求", "想去纽约"]
        results = await destination_extractor.batch_extract_destinations(texts)

        assert len(results) == 3
        assert results[0].destination == "巴黎"
        assert results[1].destination == "unknown"  # Fallback for failed extraction
        assert results[1].confidence == 0.0
        assert results[2].destination == "纽约"

    @pytest.mark.asyncio
    async def test_extract_destination_confidence_clamping(self, destination_extractor, mock_gemini_client):
        """Test that confidence values are clamped to [0.0, 1.0]."""
        # Test with confidence > 1.0
        mock_gemini_client.generate_json = AsyncMock(
            return_value='{"destination": "巴黎", "country": "法国", "confidence": 1.5}'
        )
        result = await destination_extractor.extract_destination("test")
        assert result.confidence == 1.0

        # Test with confidence < 0.0
        mock_gemini_client.generate_json = AsyncMock(
            return_value='{"destination": "巴黎", "country": "法国", "confidence": -0.5}'
        )
        result = await destination_extractor.extract_destination("test")
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_validate_destination(self, destination_extractor, mock_gemini_client):
        """Test destination validation."""
        mock_gemini_client.generate_json = AsyncMock(
            return_value='{"is_valid": true, "country": "法国"}'
        )

        is_valid, country = await destination_extractor.validate_destination("巴黎")

        assert is_valid is True
        assert country == "法国"


class TestGeminiClient:
    """Test cases for GeminiClient."""

    def test_client_initialization_with_api_key(self):
        """Test client initialization with API key."""
        client = GeminiClient(api_key="test_key", model="test-model")
        assert client.api_key == "test_key"
        assert client.model == "test-model"

    def test_client_initialization_without_api_key_raises_error(self, monkeypatch):
        """Test client initialization without API key raises ValueError."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Google API key not found"):
            GeminiClient()

    def test_health_check(self):
        """Test health check returns True when API key is set."""
        with patch("app.agent.gemini_client.GeminiClient.__init__", return_value=None):
            client = GeminiClient.__new__(GeminiClient)
            client.api_key = "test_key"
            assert client.health_check() is True

    def test_health_check_no_api_key(self):
        """Test health check returns False when API key is not set."""
        with patch("app.agent.gemini_client.GeminiClient.__init__", return_value=None):
            client = GeminiClient.__new__(GeminiClient)
            client.api_key = None
            assert client.health_check() is False
