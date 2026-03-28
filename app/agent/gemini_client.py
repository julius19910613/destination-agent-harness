"""Gemini client for interacting with Google's Generative AI API."""
import os
import logging
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini client.

        Args:
            api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
            model: Model name to use. If None, reads from GEMINI_MODEL env var or defaults to gemini-1.5-flash.

        Raises:
            ValueError: If API key is not provided or found in environment.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key not found. Please provide api_key parameter or "
                "set GOOGLE_API_KEY environment variable."
            )
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"Gemini client initialized with model: {self.model}")

    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate content using Gemini.

        Args:
            prompt: The prompt to send to Gemini.
            temperature: Controls randomness (0.0 to 2.0). Lower = more deterministic.
            max_output_tokens: Maximum number of tokens in the response.

        Returns:
            Generated text response.

        Raises:
            Exception: If the API call fails.
        """
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            )

            if max_output_tokens:
                config.max_output_tokens = max_output_tokens

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text

        except Exception as e:
            logger.error(f"Error generating content from Gemini: {e}")
            raise

    async def generate_json(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate JSON content using Gemini.

        This is a convenience method that ensures JSON output format.

        Args:
            prompt: The prompt to send to Gemini.
            temperature: Controls randomness (0.0 to 2.0). Lower = more deterministic.
            max_output_tokens: Maximum number of tokens in the response.

        Returns:
            Generated JSON string.
        """
        return await self.generate_content(
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    def health_check(self) -> bool:
        """
        Check if the Gemini client is properly configured.

        Returns:
            True if client is configured, False otherwise.
        """
        try:
            return bool(self.api_key)
        except Exception:
            return False


# Global client instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Get or create the global Gemini client instance.

    Returns:
        The global Gemini client instance.

    Raises:
        ValueError: If the client cannot be initialized.
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
