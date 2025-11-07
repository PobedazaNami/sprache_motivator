import redis.asyncio as redis
from typing import Optional
import json
import hashlib
from bot.config import settings


class RedisService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    def _generate_cache_key(self, source_text: str, source_lang: str, target_lang: str) -> str:
        """Generate a hash-based cache key to handle long texts"""
        # Create a hash of the source text for consistent, short keys
        text_hash = hashlib.sha256(source_text.encode('utf-8')).hexdigest()[:16]
        return f"translation:{source_lang}:{target_lang}:{text_hash}"
    
    async def get_cached_translation(self, source_text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""
        key = self._generate_cache_key(source_text, source_lang, target_lang)
        return await self.redis.get(key)
    
    async def cache_translation(self, source_text: str, source_lang: str, target_lang: str, translation: str):
        """Cache translation"""
        key = self._generate_cache_key(source_text, source_lang, target_lang)
        await self.redis.setex(key, settings.CACHE_TTL_SECONDS, translation)
    
    async def get_user_tokens_today(self, user_id: int) -> int:
        """Get user's token usage for today"""
        key = f"tokens:user:{user_id}"
        tokens = await self.redis.get(key)
        return int(tokens) if tokens else 0
    
    async def increment_user_tokens(self, user_id: int, tokens: int) -> int:
        """Increment user's token usage"""
        key = f"tokens:user:{user_id}"
        new_total = await self.redis.incrby(key, tokens)
        # Set expiry to end of day (simplified: 24 hours)
        await self.redis.expire(key, 86400)
        return new_total
    
    async def set_user_state(self, user_id: int, state: str, data: dict = None):
        """Set user state for conversations"""
        key = f"state:user:{user_id}"
        value = json.dumps({"state": state, "data": data or {}})
        await self.redis.setex(key, 3600, value)  # 1 hour expiry
    
    async def get_user_state(self, user_id: int) -> Optional[dict]:
        """Get user state"""
        key = f"state:user:{user_id}"
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def clear_user_state(self, user_id: int):
        """Clear user state"""
        key = f"state:user:{user_id}"
        await self.redis.delete(key)


redis_service = RedisService()
