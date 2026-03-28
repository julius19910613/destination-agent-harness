"""Destination extraction agent using Google Gemini (with Harness Phase 2)."""
import json
import logging
import time
from typing import Optional
from app.models.schemas import DestinationExtractionResponse
from app.agent.gemini_client import GeminiClient, get_gemini_client
from app.agent.prompts import build_destination_extraction_prompt
from app.agent.tools.language_detector import LanguageDetectorTool
from app.agent.tools.cache_manager import CacheManager
from app.monitoring.error_tracking import RetryWithBackoff, CircuitBreaker
from app.monitoring.metrics import (
    track_request_metrics,
    GEMINI_API_CALLS,
    GEMINI_API_LATENCY
)

logger = logging.getLogger(__name__)


class DestinationExtractor:
    """Agent for extracting destinations from natural language (with Harness Phase 2)."""

    def __init__(self, client: Optional[GeminiClient] = None):
        """
        Initialize the destination extractor.

        Args:
            client: Optional Gemini client. If None, uses global instance.
        """
        self.client = client or get_gemini_client()

        # Initialize Harness tools
        self.language_detector = LanguageDetectorTool()
        self.cache = CacheManager(ttl=3600)  # 1 hour cache

        logger.info("DestinationExtractor initialized with Harness Phase 2 tools")

    @RetryWithBackoff(max_retries=3, base_delay=1.0)
    async def extract_destination(self, text: str) -> DestinationExtractionResponse:
        """
        Extract destination information with Harness workflow.

        Workflow:
        1. Check cache
        2. Detect language
        3. Extract destination
        4. Cache result
        5. Return response

        Args:
            text: User's natural language input (e.g., "我想去巴黎旅游").

        Returns:
            DestinationExtractionResponse with extracted destination info.

        Raises:
            ValueError: If the text is empty or invalid.
            Exception: If the extraction fails after retries.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        start_time = time.time()

        try:
            # Step 1: Check cache
            cached_result = await self.cache.get(text)
            if cached_result:
                logger.info(f"Returning cached result for: {text[:50]}")
                return cached_result

            # Step 2: Detect language
            lang_result = await self.language_detector.execute(text)
            language = lang_result["language"]
            logger.info(f"Detected language: {language}")

            # Step 3: Extract destination (with metrics tracking)
            prompt = build_destination_extraction_prompt(text)
            
            gemini_start = time.time()
            response_text = await self.client.generate_json(prompt)
            gemini_duration = time.time() - gemini_start
            
            # Track Gemini API metrics
            GEMINI_API_CALLS.labels(status="success").inc()
            GEMINI_API_LATENCY.observe(gemini_duration)

            # Step 4: Parse response
            if response_text.startswith("```"):
                response_text = response_text.strip("```json").strip("```").strip()

            extraction_data = json.loads(response_text)

            # Step 5: Build response
            destination = extraction_data.get("destination", "unknown")
            country = extraction_data.get("country")
            confidence = float(extraction_data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            response = DestinationExtractionResponse(
                destination=destination,
                country=country,
                confidence=confidence,
                raw_text=text.strip(),
            )

            # Step 6: Cache result
            await self.cache.set(text, response)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Extracted destination: {destination} "
                f"(confidence: {confidence:.2f}, language: {language}, "
                f"duration: {duration_ms:.2f}ms)"
            )

            return response

        except Exception as e:
            # Track Gemini API error
            GEMINI_API_CALLS.labels(status="error").inc()
            logger.error(f"Error extracting destination: {e}")
            raise

    async def batch_extract_destinations(
        self, texts: list[str]
    ) -> list[DestinationExtractionResponse]:
        """
        Extract destinations from multiple texts.

        Args:
            texts: List of natural language inputs.

        Returns:
            List of DestinationExtractionResponse objects.

        Raises:
            ValueError: If texts list is empty.
        """
        if not texts:
            raise ValueError("Cannot extract from empty text list")

        results = []
        for text in texts:
            try:
                result = await self.extract_destination(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract from text '{text}': {e}")
                # Return a fallback response for failed extractions
                results.append(
                    DestinationExtractionResponse(
                        destination="unknown",
                        country=None,
                        confidence=0.0,
                        raw_text=text,
                    )
                )

        return results

    async def validate_destination(
        self, destination: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a destination name is recognizable.

        Args:
            destination: Destination name to validate.

        Returns:
            Tuple of (is_valid, country).
        """
        validation_prompt = f"""Is "{destination}" a valid destination?
Respond with JSON:
{{
  "is_valid": true/false,
  "country": "country name or null"
}}"""

        try:
            response = await self.client.generate_json(validation_prompt)
            data = json.loads(response)
            return data.get("is_valid", False), data.get("country")
        except Exception as e:
            logger.error(f"Error validating destination: {e}")
            return False, None


# Global extractor instance with circuit breaker
_destination_extractor: Optional[DestinationExtractor] = None


@CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
async def get_destination_extractor() -> DestinationExtractor:
    """
    Get or create the global destination extractor instance with circuit breaker.

    Returns:
        The global DestinationExtractor instance.

    Raises:
        Exception: If circuit breaker is open.
    """
    global _destination_extractor
    if _destination_extractor is None:
        _destination_extractor = DestinationExtractor()
    return _destination_extractor
