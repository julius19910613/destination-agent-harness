"""Language detection tool."""
from langdetect import detect, LangDetectException
from typing import Dict, Any
import logging
import time
from app.monitoring.metrics import track_tool_metrics

logger = logging.getLogger(__name__)


class LanguageDetectorTool:
    """Language detection tool with metrics tracking."""

    @property
    def name(self) -> str:
        """Tool name."""
        return "detect_language"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Detect text language (ISO 639-1 code)"

    @track_tool_metrics('language_detector')
    async def execute(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Execute language detection.

        Args:
            text: Text to detect language from.

        Returns:
            {
                "language": "zh",
                "confidence": 0.9
            }
        """
        try:
            lang = detect(text)
            logger.info(f"Detected language: {lang} for text: {text[:50]}")

            return {
                "language": lang,
                "confidence": 0.9
            }

        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return {
                "language": "unknown",
                "confidence": 0.0
            }
