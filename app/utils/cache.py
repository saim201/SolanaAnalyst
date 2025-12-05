"""
Simple caching utilities.
"""
from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Callable, Optional


class SimpleCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self):
        self._cache = {}
        self._timestamps = {}

    def get(self, key: str, ttl_seconds: Optional[int] = None) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            ttl_seconds: Time to live in seconds (None = no expiry check)
            
        Returns:
            Cached value or None if expired/not found
        """
        if key not in self._cache:
            return None

        if ttl_seconds is not None:
            timestamp = self._timestamps.get(key)
            if timestamp and (datetime.now() - timestamp).seconds > ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                return None

        return self._cache[key]

    def set(self, key: str, value: Any):
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

    def clear(self):
        """Clear all cached values"""
        self._cache.clear()
        self._timestamps.clear()


# Global cache instance
_cache = SimpleCache()


def cached(ttl_seconds: int = 300):
    """
    Decorator to cache function results with TTL.
    
    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            cached_result = _cache.get(cache_key, ttl_seconds)
            if cached_result is not None:
                return cached_result

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result)
            return result

        return wrapper
    return decorator
