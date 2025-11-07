from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Database
    POSTGRES_DB: str = "sprache_bot"
    POSTGRES_USER: str = "sprache_user"
    POSTGRES_PASSWORD: str = "sprache_password"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # Admin
    ADMIN_IDS: str = ""
    
    # Bot Config
    MAX_CONCURRENT_USERS: int = 100
    DAILY_TRAINER_TIMES: str = "08:00,14:00,20:00"
    
    # Token Limits
    MAX_TOKENS_PER_USER_DAILY: int = 10000
    CACHE_TTL_SECONDS: int = 2592000  # 30 days
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
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
    
    class Config:
        env_file = ".env"


settings = Settings()
