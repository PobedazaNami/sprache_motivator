"""
Scheduler service for managing individual user training schedules
"""
import asyncio
import random
from datetime import datetime, time, timedelta
from typing import List
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from bot.models.database import User, UserStatus, async_session_maker
from bot.services.database_service import UserService
from bot.handlers import trainer
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing training schedules"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone='Europe/Kiev')
        self.bot = None
    
    def set_bot(self, bot: Bot):
        """Set bot instance"""
        self.bot = bot
    
    async def start(self):
        """Start scheduler"""
        # Check every 5 minutes for users who need tasks
        self.scheduler.add_job(
            self._check_and_send_tasks,
            'interval',
            minutes=5,
            id='check_tasks',
            replace_existing=True
        )
        
        # Daily report at 23:00 Kyiv time
        self.scheduler.add_job(
            self._send_daily_reports,
            CronTrigger(hour=23, minute=0, timezone='Europe/Kiev'),
            id='daily_report',
            replace_existing=True
        )
        
        # Weekly report on Sunday at 23:00 Kyiv time
        self.scheduler.add_job(
            self._send_weekly_reports,
            CronTrigger(day_of_week='sun', hour=23, minute=0, timezone='Europe/Kiev'),
            id='weekly_report',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started with individual user scheduling")
    
    async def _check_and_send_tasks(self):
        """Check which users need tasks now and send them"""
        if not self.bot:
            return
        
        async with async_session_maker() as session:
            # Get all users with enabled trainer
            users = await UserService.get_users_with_trainer_enabled(session)
            
            now_kyiv = datetime.now(ZoneInfo('Europe/Kyiv'))
            current_time = now_kyiv.time()
            current_date = now_kyiv.date()
            
            for user in users:
                try:
                    # Check if user should receive task now
                    if await self._should_send_task(user, current_time, current_date):
                        await trainer.send_training_task(self.bot, user.telegram_id)
                        await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Failed to send task to user {user.telegram_id}: {e}")
    
    async def _should_send_task(self, user: User, current_time: time, current_date) -> bool:
        """
        Determine if user should receive a task now based on their settings
        Returns True if task should be sent
        """
        # Parse user's time window
        start_time = time.fromisoformat(user.trainer_start_time or "09:00")
        end_time = time.fromisoformat(user.trainer_end_time or "21:00")
        
        # Check if current time is within user's window
        if not (start_time <= current_time <= end_time):
            return False
        
        # Get user's task count for today from Redis
        from bot.services.redis_service import redis_service
        tasks_today_key = f"tasks_today:{user.id}:{current_date}"
        tasks_sent = await redis_service.get(tasks_today_key)
        tasks_sent = int(tasks_sent) if tasks_sent else 0
        
        messages_per_day = user.trainer_messages_per_day or 3
        
        if tasks_sent >= messages_per_day:
            return False  # Already sent all tasks for today
        
        # Calculate time slots within user's window
        window_minutes = self._time_diff_minutes(start_time, end_time)
        slot_size = window_minutes // messages_per_day
        
        # Determine which slot we're in
        minutes_since_start = self._time_diff_minutes(start_time, current_time)
        current_slot = minutes_since_start // slot_size
        
        # Check if we already sent a task for this slot
        last_slot_key = f"last_slot:{user.id}:{current_date}"
        last_slot = await redis_service.get(last_slot_key)
        last_slot = int(last_slot) if last_slot else -1
        
        if current_slot > last_slot:
            # Time to send task for this slot
            # Update counters
            await redis_service.set(tasks_today_key, tasks_sent + 1, ex=86400)  # Expire in 24h
            await redis_service.set(last_slot_key, current_slot, ex=86400)
            return True
        
        return False
    
    def _time_diff_minutes(self, start: time, end: time) -> int:
        """Calculate difference between two times in minutes"""
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        return end_minutes - start_minutes
    
    async def _send_daily_reports(self):
        """Send daily statistics to all active users"""
        if not self.bot:
            return
        
        from bot.models.database import DailyStats
        from bot.locales.texts import get_text
        from sqlalchemy import select
        from datetime import timezone
        
        logger.info("Sending daily reports...")
        
        async with async_session_maker() as session:
            users = await UserService.get_users_with_trainer_enabled(session)
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            for user in users:
                try:
                    # Get today's stats
                    result = await session.execute(
                        select(DailyStats).where(
                            DailyStats.user_id == user.id,
                            DailyStats.date == today
                        )
                    )
                    stats = result.scalar_one_or_none()
                    
                    if not stats or stats.completed_tasks == 0:
                        continue  # Skip if no tasks completed
                    
                    lang = user.interface_language.value
                    
                    # Generate motivation message
                    motivation = self._get_motivation_message(stats.average_quality, lang)
                    
                    message = get_text(lang, "daily_report",
                                      completed=stats.completed_tasks,
                                      total=stats.total_tasks,
                                      quality=stats.average_quality,
                                      motivation=motivation)
                    
                    await self.bot.send_message(user.telegram_id, message)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send daily report to {user.telegram_id}: {e}")
    
    async def _send_weekly_reports(self):
        """Send weekly statistics to all active users"""
        if not self.bot:
            return
        
        from bot.models.database import DailyStats
        from bot.locales.texts import get_text
        from sqlalchemy import select, func
        from datetime import timezone
        
        logger.info("Sending weekly reports...")
        
        async with async_session_maker() as session:
            users = await UserService.get_users_with_trainer_enabled(session)
            
            # Calculate week start (Monday)
            today = datetime.now(timezone.utc)
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            for user in users:
                try:
                    # Get week's stats
                    result = await session.execute(
                        select(
                            func.sum(DailyStats.completed_tasks),
                            func.sum(DailyStats.total_tasks),
                            func.avg(DailyStats.average_quality)
                        ).where(
                            DailyStats.user_id == user.id,
                            DailyStats.date >= week_start
                        )
                    )
                    row = result.first()
                    
                    if not row or not row[0]:
                        continue  # Skip if no tasks completed
                    
                    completed, total, avg_quality = row
                    avg_quality = int(avg_quality) if avg_quality else 0
                    
                    lang = user.interface_language.value
                    achievement = self._get_achievement_message(avg_quality, completed, lang)
                    
                    message = get_text(lang, "weekly_report",
                                      completed=completed or 0,
                                      total=total or 0,
                                      quality=avg_quality,
                                      achievement=achievement)
                    
                    await self.bot.send_message(user.telegram_id, message)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send weekly report to {user.telegram_id}: {e}")
    
    def _get_motivation_message(self, quality: int, lang: str) -> str:
        """Get motivational message based on quality"""
        if lang == "uk":
            if quality >= 90:
                return "🏆 Відмінно! Ви володієте мовою на високому рівні!"
            elif quality >= 75:
                return "💪 Чудові результати! Продовжуйте в тому ж дусі!"
            elif quality >= 60:
                return "👍 Добре! Ще трохи практики і будете експертом!"
            else:
                return "💪 Не здавайтесь! Кожен день ви стаєте кращими!"
        else:  # ru
            if quality >= 90:
                return "🏆 Отлично! Вы владеете языком на высоком уровне!"
            elif quality >= 75:
                return "💪 Отличные результаты! Продолжайте в том же духе!"
            elif quality >= 60:
                return "👍 Хорошо! Ещё немного практики и будете экспертом!"
            else:
                return "💪 Не сдавайтесь! Каждый день вы становитесь лучше!"
    
    def _get_achievement_message(self, quality: int, tasks: int, lang: str) -> str:
        """Get achievement message for weekly report"""
        if lang == "uk":
            if quality >= 90 and tasks >= 15:
                return "Ви досягли майстерності! Неймовірно! 🌟"
            elif quality >= 80:
                return "Чудовий тиждень! Ви робите величезний прогрес! 🎯"
            elif quality >= 70:
                return "Solid week! Keep it up! 💪"
            else:
                return "Головне - не здаватись! Наступного тижня буде краще! 🚀"
        else:  # ru
            if quality >= 90 and tasks >= 15:
                return "Вы достигли мастерства! Невероятно! 🌟"
            elif quality >= 80:
                return "Отличная неделя! Вы делаете огромный прогресс! 🎯"
            elif quality >= 70:
                return "Хорошая неделя! Так держать! 💪"
            else:
                return "Главное - не сдаваться! На следующей неделе будет лучше! 🚀"


# Global instance
scheduler_service = SchedulerService()
