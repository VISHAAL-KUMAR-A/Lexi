"""Simple TTL cache implementation for caching states and commissions data."""

import asyncio
import time
from typing import Any, Dict, Optional, TypeVar

from app.core.config import get_settings
from app.core.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class TTLCache:
    """Simple in-memory TTL (Time To Live) cache implementation."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache if it hasn't expired."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            current_time = time.time()

            if current_time > entry["expires_at"]:
                # Entry has expired, remove it
                del self._cache[key]
                logger.debug(f"Cache key '{key}' expired and removed")
                return None

            logger.debug(f"Cache hit for key '{key}'")
            return entry["value"]

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set a value in the cache with a TTL in seconds."""
        async with self._lock:
            expires_at = time.time() + ttl
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
            }
            logger.debug(f"Cache key '{key}' set with TTL {ttl} seconds")

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache key '{key}' deleted")
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if current_time > entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(
                    f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = 0
        expired_entries = 0

        for entry in self._cache.values():
            if current_time > entry["expires_at"]:
                expired_entries += 1
            else:
                active_entries += 1

        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": expired_entries,
        }


# Global cache instance
_cache_instance: Optional[TTLCache] = None


def get_cache() -> TTLCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TTLCache()
    return _cache_instance


# Cache key constants
STATES_CACHE_KEY = "jagriti:states"
COMMISSIONS_CACHE_KEY_PREFIX = "jagriti:commissions:"


async def get_cached_states() -> Optional[Any]:
    """Get cached states data."""
    cache = get_cache()
    return await cache.get(STATES_CACHE_KEY)


async def set_cached_states(states_data: Any) -> None:
    """Cache states data."""
    settings = get_settings()
    cache = get_cache()
    await cache.set(STATES_CACHE_KEY, states_data, settings.cache_ttl_states)


async def get_cached_commissions(state_id: str) -> Optional[Any]:
    """Get cached commissions data for a specific state."""
    cache = get_cache()
    cache_key = f"{COMMISSIONS_CACHE_KEY_PREFIX}{state_id}"
    return await cache.get(cache_key)


async def set_cached_commissions(state_id: str, commissions_data: Any) -> None:
    """Cache commissions data for a specific state."""
    settings = get_settings()
    cache = get_cache()
    cache_key = f"{COMMISSIONS_CACHE_KEY_PREFIX}{state_id}"
    await cache.set(cache_key, commissions_data, settings.cache_ttl_commissions)


async def clear_all_cache() -> None:
    """Clear all cached data."""
    cache = get_cache()
    await cache.clear()


async def cleanup_expired_cache() -> int:
    """Clean up expired cache entries."""
    cache = get_cache()
    return await cache.cleanup_expired()
