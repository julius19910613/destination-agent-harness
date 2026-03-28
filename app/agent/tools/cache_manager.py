"""Cache manager for destination extraction results."""
import time
from typing import Any, Optional, Dict
import hashlib
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Simple in-memory cache with TTL support and metrics tracking."""

    def __init__(self, ttl: int = 3600):
        """
        Initialize cache manager.

        Args:
            ttl: Cache time-to-live in seconds (default: 1 hour).
        """
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
        self._hits = 0
        self._misses = 0
        logger.info(f"CacheManager initialized with TTL={ttl}s")

    def _generate_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    async def get(self, text: str) -> Optional[Any]:
        """
        Get cached result for text.

        Args:
            text: Input text.

        Returns:
            Cached result or None if not found/expired.
        """
        key = self._generate_key(text)

        if key in self.cache:
            value, timestamp = self.cache[key]

            # Check if expired
            if time.time() - timestamp < self.ttl:
                logger.info(f"Cache hit for key: {key[:8]}")
                self._hits += 1
                # Don't track metrics here - track at higher level
                return value
            else:
                # Expired, remove it
                del self.cache[key]
                logger.info(f"Cache expired for key: {key[:8]}")

        self._misses += 1
        return None

    async def set(self, text: str, value: Any):
        """
        Set cache for text.

        Args:
            text: Input text.
            value: Value to cache.
        """
        key = self._generate_key(text)
        self.cache[key] = (value, time.time())
        logger.info(f"Cache set for key: {key[:8]}")

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_items": len(self.cache),
            "ttl": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2)
        }
