"""Security utilities (Phase 5)."""
import os
import re
import time
from typing import Optional
from functools import wraps
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import APIKeyHeader
import logging

logger = logging.getLogger(__name__)

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class InputValidator:
    """Input validation utilities."""

    @staticmethod
    def validate_text(text: str, max_length: int = 1000) -> str:
        """
        Validate and sanitize input text.

        Args:
            text: Input text.
            max_length: Maximum allowed length.

        Returns:
            Sanitized text.

        Raises:
            ValueError: If validation fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Length check
        if len(text) > max_length:
            raise ValueError(f"Text too long (max {max_length} characters)")

        # Remove dangerous characters
        text = re.sub(r'<[^>]*>', '', text)  # Remove HTML tags
        text = re.sub(r'[<>\"\'\\]', '', text)  # Remove special chars

        return text.strip()

    @staticmethod
    def detect_injection(text: str) -> bool:
        """
        Detect potential injection attacks.

        Args:
            text: Input text.

        Returns:
            True if injection detected.
        """
        patterns = [
            r'(?i)(select|insert|update|delete|drop|create|alter)',  # SQL
            r'(?i)(script|javascript|vbscript)',  # XSS
            r'(?i)(eval|exec|system|shell)',  # Code injection
            r'(?i)(union.*select)',  # SQL union
            r'(?i)(or\s+1\s*=\s*1)',  # SQL injection
        ]

        for pattern in patterns:
            if re.search(pattern, text):
                logger.warning(f"Injection detected: {text[:50]}")
                return True

        return False

    @staticmethod
    def sanitize_destination(destination: str) -> str:
        """
        Sanitize destination name.

        Args:
            destination: Destination name.

        Returns:
            Sanitized name.
        """
        # Remove numbers and special characters (keep unicode letters and spaces)
        sanitized = re.sub(r'[^\w\s\u4e00-\u9fff]', '', destination)
        return sanitized.strip()


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute.
            requests_per_hour: Max requests per hour.
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests = {}  # {ip: [(timestamp, ...)]}

    def check_rate_limit(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if rate limit exceeded.

        Args:
            identifier: Client identifier (IP or API key).

        Returns:
            (allowed, metadata)
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                ts for ts in self.requests[identifier]
                if ts > hour_ago
            ]

        # Get recent requests
        recent_minute = sum(
            1 for ts in self.requests.get(identifier, [])
            if ts > minute_ago
        )
        recent_hour = len(self.requests.get(identifier, []))

        # Check limits
        if recent_minute >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded (minute): {identifier} "
                f"({recent_minute}/{self.requests_per_minute})"
            )
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded_minute",
                "retry_after": 60 - (now - minute_ago),
                "limit": self.requests_per_minute,
                "current": recent_minute
            }

        if recent_hour >= self.requests_per_hour:
            logger.warning(
                f"Rate limit exceeded (hour): {identifier} "
                f"({recent_hour}/{self.requests_per_hour})"
            )
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded_hour",
                "retry_after": 3600 - (now - hour_ago),
                "limit": self.requests_per_hour,
                "current": recent_hour
            }

        # Record request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(now)

        return True, {
            "allowed": True,
            "minute": {"current": recent_minute + 1, "limit": self.requests_per_minute},
            "hour": {"current": recent_hour + 1, "limit": self.requests_per_hour}
        }


# Global rate limiter
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# Authentication dependency
async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    """
    Verify API Key (optional).

    If X-API-Key header is provided, validate it.
    If not provided, allow access (for demo/testing).

    Args:
        api_key: API key from header.

    Returns:
        API key or None.

    Raises:
        HTTPException: If API key is invalid.
    """
    # If no API key provided, allow access
    if not api_key:
        return None

    # Get valid keys from environment
    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")

    if api_key not in valid_keys:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

    logger.info(f"API key validated: {api_key[:8]}...")
    return api_key


# Rate limiting dependency
async def check_rate_limit(request: Request):
    """
    Check rate limit.

    Args:
        request: FastAPI request.

    Raises:
        HTTPException: If rate limit exceeded.
    """
    limiter = get_rate_limiter()

    # Get client identifier (IP or API key)
    identifier = request.client.host
    api_key = request.headers.get("X-API-Key")
    if api_key:
        identifier = f"apikey:{api_key[:16]}"

    allowed, metadata = limiter.check_rate_limit(identifier)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=metadata
        )

    return metadata


# Combined dependency
async def security_check(
    request: Request,
    api_key: Optional[str] = Depends(verify_api_key),
    rate_limit: dict = Depends(check_rate_limit)
):
    """
    Combined security check (auth + rate limit).

    Args:
        request: Request object.
        api_key: Validated API key (optional).
        rate_limit: Rate limit metadata.

    Returns:
        Security context.
    """
    return {
        "api_key": api_key,
        "rate_limit": rate_limit,
        "client_ip": request.client.host
    }
