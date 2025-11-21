from pydantic_settings import BaseSettings
from pydantic import ValidationError
from typing import List


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # MongoDB (required)
    # Example: mongodb+srv://user:pass@cluster/dbname
    MONGODB_URI: str
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # LanguageTool grammar server
    # Example: http://languagetool:8010 or http://localhost:8010
    LANGUAGETOOL_URL: str = "http://languagetool:8010"
    LANGUAGETOOL_ENABLED: bool = True
    
    # Admin
    ADMIN_IDS: str = ""
    
    # Bot Config
    MAX_CONCURRENT_USERS: int = 100
    DAILY_TRAINER_TIMES: str = "08:00,14:00,20:00"
    
    # Token Limits
    MAX_TOKENS_PER_USER_DAILY: int = 10000
    CACHE_TTL_SECONDS: int = 2592000  # 30 days
    
    # Subscription
    STRIPE_PAYMENT_LINK: str = ""  # Stripe payment link for €4/month subscription (translator only)
    ADMIN_CONTACT: str = "@reeziat"  # Admin contact for support
    
    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"
    
    @property
    def admin_id_list(self) -> List[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]
    
    @property
    def trainer_times(self) -> List[str]:
        return [x.strip() for x in self.DAILY_TRAINER_TIMES.split(",")]
    
    @property
    def mongo_enabled(self) -> bool:
        """Check if MongoDB URI is provided and valid"""
        return bool(self.MONGODB_URI and self.MONGODB_URI.startswith("mongodb"))
    
    class Config:
        env_file = ".env"


# Safe settings initialization:
# In CI/tests there may be no environment variables; avoid import-time crashes.
try:
    settings = Settings()
except ValidationError:
    # Fallback minimal values for test import context only.
    # Runtime must provide real values via environment/.env
    settings = Settings(
        BOT_TOKEN="test_token",
        OPENAI_API_KEY="test_key",
        MONGODB_URI="mongodb://localhost:27017/sprache_motivator"
    )
