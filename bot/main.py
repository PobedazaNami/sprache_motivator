import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import Redis

from bot.config import settings
from bot.models.database import init_db, async_session_maker
from bot.services.redis_service import redis_service
from bot.services.database_service import UserService
from bot.services.scheduler_service import scheduler_service
from bot.handlers import start, translator, trainer, settings as settings_handler, admin, friends, express_trainer, flashcards
from bot.models.database import UserStatus
from bot.services import mongo_service


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot function"""
    # Initialize database
    logger.info("Initializing database...")
    logger.info(f"Admin IDs configured: {settings.admin_id_list}")
    await init_db()
    
    # Initialize Redis
    logger.info("Connecting to Redis...")
    await redis_service.connect()

    # Optional MongoDB initialization
    if settings.mongo_enabled:
        logger.info("Initializing MongoDB (optional)...")
        try:
            initialized = await mongo_service.init()
            if initialized:
                logger.info("MongoDB initialized successfully")
            else:
                logger.warning("MongoDB URI present but initialization returned False")
        except Exception as e:
            logger.error(f"MongoDB initialization failed: {e}")
    
    # Create bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Use RedisStorage for FSM persistence if available
    try:
        redis_client = Redis.from_url(settings.redis_url)
        storage = RedisStorage(redis=redis_client, key_builder=DefaultKeyBuilder(with_destiny=True))
        logger.info("Using RedisStorage for FSM")
    except Exception as e:
        logger.error(f"Failed to initialize RedisStorage: {e}. Falling back to MemoryStorage.")
        storage = MemoryStorage()
        
    dp = Dispatcher(storage=storage)
    
    # Register handlers (order matters - more specific handlers first)
    dp.include_router(start.router)
    dp.include_router(translator.router)
    dp.include_router(settings_handler.router)
    dp.include_router(friends.router)
    dp.include_router(admin.router)
    dp.include_router(flashcards.router)
    # Express trainer router before trainer because both have text handlers
    dp.include_router(express_trainer.router)
    # Trainer router last because it has a catch-all text handler
    dp.include_router(trainer.router)
    
    # Start new scheduler service with individual user scheduling
    logger.info("Starting scheduler service...")
    scheduler_service.set_bot(bot)
    await scheduler_service.start()
    
    try:
        logger.info("Bot started!")
        await dp.start_polling(bot)
    finally:
        # Cleanup
        logger.info("Shutting down...")
        scheduler_service.scheduler.shutdown()
        await redis_service.disconnect()
        # Mongo does not require explicit close; relying on motor's internal cleanup.
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
