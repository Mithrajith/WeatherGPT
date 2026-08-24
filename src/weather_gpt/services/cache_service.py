import json
import time
import logging
from typing import Any, Optional
from weather_gpt.config import settings

logger = logging.getLogger("weather_gpt.cache")

class MemoryCache:
    """Fallback in-memory cache when Redis is unreachable."""
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            val, expire_at = self._store[key]
            if time.time() < expire_at:
                return val
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 1800) -> None:
        expire_at = time.time() + ttl_seconds
        self._store[key] = (value, expire_at)

class CacheService:
    def __init__(self):
        self.memory_cache = MemoryCache()
        self.redis_client = None
        self._redis_available = False
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1)
            self.redis_client.ping()
            self._redis_available = True
            logger.info("Successfully connected to Redis server.")
        except Exception as e:
            self._redis_available = False
            logger.warning(f"Redis connection unavailable ({e}). Falling back to In-Memory Cache.")

    async def get(self, key: str) -> Optional[Any]:
        if self._redis_available and self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}. Checking memory cache.")
        return self.memory_cache.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int = settings.CACHE_TTL_SECONDS) -> None:
        json_data = json.dumps(value, default=str)
        if self._redis_available and self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, json_data)
                return
            except Exception as e:
                logger.warning(f"Redis set failed: {e}. Falling back to memory cache.")
        self.memory_cache.set(key, value, ttl_seconds)

cache_service = CacheService()
