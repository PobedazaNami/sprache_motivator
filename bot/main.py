import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.models.database import init_db, async_session_maker
from bot.services.redis_service import redis_service
from bot.services.database_service import UserService
from bot.handlers import start, translator, trainer, settings as settings_handler, admin
from bot.models.database import UserStatus


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def send_daily_tasks(bot: Bot):
    """Send daily training tasks to all users with trainer enabled"""
    logger.info("Sending daily training tasks...")
    
    async with async_session_maker() as session:
        from sqlalchemy import select
        from bot.models.database import User
        
        result = await session.execute(
            select(User).where(
                User.status == UserStatus.APPROVED,
                User.daily_trainer_enabled == True
            )
        )
        users = result.scalars().all()
        
        for user in users:
            try:
                await trainer.send_training_task(bot, user.telegram_id)
                await asyncio.sleep(0.1)  # Avoid hitting rate limits
            except Exception as e:
                logger.error(f"Failed to send task to user {user.telegram_id}: {e}")
        
        logger.info(f"Sent training tasks to {len(users)} users")


async def schedule_daily_tasks(bot: Bot):
    """Schedule daily tasks at configured times"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = AsyncIOScheduler()
    
    # Schedule tasks at configured times
    for time_str in settings.trainer_times:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            send_daily_tasks,
            CronTrigger(hour=hour, minute=minute),
            args=[bot],
            id=f"daily_task_{time_str}",
            replace_existing=True
        )
        logger.info(f"Scheduled daily task at {time_str}")
    
    scheduler.start()
    return scheduler


async def main():
    """Main bot function"""
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    
    # Initialize Redis
    logger.info("Connecting to Redis...")
    await redis_service.connect()
    
    # Create bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register handlers
    dp.include_router(start.router)
    dp.include_router(translator.router)
    dp.include_router(trainer.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin.router)
    
    # Start scheduler
    logger.info("Starting scheduler...")
    scheduler = await schedule_daily_tasks(bot)
    
    try:
        logger.info("Bot started!")
        await dp.start_polling(bot)
    finally:
        # Cleanup
        logger.info("Shutting down...")
        scheduler.shutdown()
        await redis_service.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
