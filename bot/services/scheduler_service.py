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

from bot.models.database import async_session_maker
from bot.services.database_service import UserService
from bot.handlers import trainer
from bot.services import mongo_service
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
            
            for user in users:
                try:
                    user_tz = ZoneInfo(getattr(user, 'trainer_timezone', None) or 'Europe/Berlin')
                    now_user = datetime.now(user_tz)
                    current_time = now_user.time()
                    current_date = now_user.date()
                    # Check if user should receive task now
                    if await self._should_send_task(user, current_time, current_date):
                        await trainer.send_training_task(self.bot, user.telegram_id)
                        await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Failed to send task to user {user.telegram_id}: {e}")
    
    async def _should_send_task(self, user, current_time: time, current_date) -> bool:
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
        
        # Get last task time
        last_task_time_key = f"last_task_time:{user.id}:{current_date}"
        last_task_time_str = await redis_service.get(last_task_time_key)
        
        # Calculate minimum interval between tasks
        window_minutes = self._time_diff_minutes(start_time, end_time)
        min_interval_minutes = window_minutes // messages_per_day
        
        # If this is the first task or enough time has passed
        if not last_task_time_str:
            # First task: can send it (counter will be updated after successful send)
            return True
        
        # Check if enough time has passed since last task
        last_task_time = time.fromisoformat(last_task_time_str)
        minutes_since_last = self._time_diff_minutes(last_task_time, current_time)
        
        if minutes_since_last >= min_interval_minutes:
            # Enough time has passed, can send task (counter will be updated after successful send)
            return True
        
        return False
    
    def _time_diff_minutes(self, start: time, end: time) -> int:
        """Calculate difference between two times in minutes"""
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        return end_minutes - start_minutes
    
    async def get_daily_progress(self, user) -> tuple[int, int]:
        """
        Get user's daily progress
        Returns (tasks_sent_today, total_tasks_per_day)
        """
        from bot.services.redis_service import redis_service
        
        user_tz = ZoneInfo(getattr(user, 'trainer_timezone', None) or 'Europe/Berlin')
        now_user = datetime.now(user_tz)
        current_date = now_user.date()
        
        tasks_today_key = f"tasks_today:{user.id}:{current_date}"
        tasks_sent = await redis_service.get(tasks_today_key)
        tasks_sent = int(tasks_sent) if tasks_sent else 0
        
        messages_per_day = user.trainer_messages_per_day or 3
        
        return tasks_sent, messages_per_day
    
    async def calculate_next_task_time(self, user) -> tuple[datetime | None, str]:
        """
        Calculate when the next task will be sent to the user
        Returns (next_task_datetime, formatted_countdown_string)
        If no more tasks today, returns (None, message_about_tomorrow)
        """
        from bot.services.redis_service import redis_service
        
        user_tz = ZoneInfo(getattr(user, 'trainer_timezone', None) or 'Europe/Berlin')
        now_user = datetime.now(user_tz)
        current_time = now_user.time()
        current_date = now_user.date()
        
        # Get user settings
        start_time = time.fromisoformat(user.trainer_start_time or "09:00")
        end_time = time.fromisoformat(user.trainer_end_time or "21:00")
        messages_per_day = user.trainer_messages_per_day or 3
        
        # Get tasks sent today (cap by daily limit just in case)
        tasks_today_key = f"tasks_today:{user.id}:{current_date}"
        tasks_sent = await redis_service.get(tasks_today_key)
        tasks_sent = int(tasks_sent) if tasks_sent else 0
        if tasks_sent > messages_per_day:
            tasks_sent = messages_per_day
        
        # Check if all tasks for today are complete
        if tasks_sent >= messages_per_day:
            # Next task is tomorrow at start time
            tomorrow = now_user + timedelta(days=1)
            next_task_dt = datetime.combine(tomorrow.date(), start_time, tzinfo=user_tz)
            time_diff = next_task_dt - now_user
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            return next_task_dt, f"{hours}ч {minutes}мин"
        
        # Calculate minimum interval between tasks
        window_minutes = self._time_diff_minutes(start_time, end_time)
        # Если окно слишком узкое или сообщений очень много, минимальный интервал не меньше 5 минут
        min_interval_minutes = max(5, window_minutes // messages_per_day if messages_per_day > 0 else window_minutes)
        
        # Get last task time
        last_task_time_key = f"last_task_time:{user.id}:{current_date}"
        last_task_time_str = await redis_service.get(last_task_time_key)
        
        # If we haven't started today yet
        if not last_task_time_str:
            if current_time < start_time:
                # Next task is at start time
                next_task_dt = datetime.combine(current_date, start_time, tzinfo=user_tz)
            else:
                # We're in the window but haven't sent first task yet - send soon
                next_task_dt = now_user + timedelta(minutes=5)
        else:
            # Calculate when next task should be sent based on last task time
            last_task_time = time.fromisoformat(last_task_time_str)
            last_task_minutes = last_task_time.hour * 60 + last_task_time.minute
            next_task_minutes = last_task_minutes + min_interval_minutes
            
            if next_task_minutes >= 24 * 60:
                # Next task is tomorrow
                tomorrow = now_user + timedelta(days=1)
                next_task_dt = datetime.combine(tomorrow.date(), start_time, tzinfo=user_tz)
            else:
                next_task_hour = next_task_minutes // 60
                next_task_minute = next_task_minutes % 60
                next_task_time = time(hour=next_task_hour, minute=next_task_minute)
                next_task_dt = datetime.combine(current_date, next_task_time, tzinfo=user_tz)
                
                # If next task time is beyond end time or already passed, schedule for tomorrow
                if next_task_time > end_time or next_task_dt <= now_user:
                    tomorrow = now_user + timedelta(days=1)
                    next_task_dt = datetime.combine(tomorrow.date(), start_time, tzinfo=user_tz)
        
        # Calculate time difference
        time_diff = next_task_dt - now_user
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        # Format countdown string
        if hours > 0:
            countdown = f"{hours}ч {minutes}мин"
        else:
            countdown = f"{minutes}мин"
        
        return next_task_dt, countdown
    
    async def _send_daily_reports(self):
        """Send daily statistics to all active users"""
        if not self.bot:
            return
        
        from bot.locales.texts import get_text
        
        logger.info("Sending daily reports...")
        
        async with async_session_maker() as session:
            users = await UserService.get_users_with_trainer_enabled(session)
            
            for user in users:
                try:
                    stats = await mongo_service.get_today_stats(user.telegram_id)
                    lang = user.interface_language.value
                    planned_daily = user.trainer_messages_per_day or 3
                    completed = stats.get('completed', 0) if stats else 0
                    avg_quality = stats.get('quality', 0) if stats else 0
                    stored_planned = stats.get('expected') if stats else None
                    planned = max(planned_daily, stored_planned or 0)
                    missed = max(planned - completed, 0)
                    penalty = missed * 10
                    final_score = max(0, min(100, avg_quality - penalty))
                    motivation = self._get_motivation_message(final_score, lang)
                    
                    message = get_text(
                        lang,
                        "daily_report",
                        planned=planned,
                        completed=completed,
                        missed=missed,
                        quality=avg_quality,
                        penalty=penalty,
                        final=final_score,
                        motivation=motivation,
                    )
                    
                    # Add streak information
                    streak_info = await mongo_service.get_streak(user.telegram_id)
                    if streak_info.get("current", 0) > 0:
                        message += "\n\n" + get_text(lang, "streak_message", days=streak_info["current"])
                    elif streak_info.get("broken"):
                        message += "\n\n" + get_text(lang, "streak_lost")
                    
                    # Add mastered sentences count
                    mastered_count = await mongo_service.get_mastered_count(user.telegram_id)
                    if mastered_count > 0:
                        message += "\n" + get_text(lang, "mastered_sentences_count", count=mastered_count)
                    
                    # Add friends' statistics if user has friends
                    friends_stats = await mongo_service.get_friends_stats(user.telegram_id)
                    if friends_stats:
                        friends_section = "\n\n" + get_text(lang, "friends_stats_title")
                        for friend_id, friend_stat in friends_stats.items():
                            friend = await UserService.get_or_create_user(session, friend_id)
                            friend_name = friend.first_name or friend.username or f"User {friend_id}"
                            friend_username = friend.username or str(friend_id)
                            completed = friend_stat.get("completed", 0)
                            quality = friend_stat.get("quality", 0)
                            know = friend_stat.get("flashcard_know", 0)
                            retry = friend_stat.get("flashcard_retry", 0)
                            streak_info = await mongo_service.get_streak(friend_id)
                            streak = streak_info.get("current", 0)
                            quality_line = ""
                            if completed > 0:
                                quality_line = get_text(lang, "friends_stats_quality_inline", quality=quality)

                            friends_section += get_text(
                                lang,
                                "friends_stats_user_active",
                                name=friend_name,
                                username=friend_username,
                                completed=completed,
                                know=know,
                                retry=retry,
                                quality_line=quality_line,
                                streak=streak,
                            )
                        message += friends_section
                    
                    await self.bot.send_message(user.telegram_id, message)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send daily report to {user.telegram_id}: {e}")
    
    async def _send_weekly_reports(self):
        """Send weekly statistics to all active users"""
        if not self.bot:
            return
        
        from bot.locales.texts import get_text
        
        logger.info("Sending weekly reports...")
        
        async with async_session_maker() as session:
            users = await UserService.get_users_with_trainer_enabled(session)
            
            for user in users:
                try:
                    # Get week's stats from MongoDB
                    week_stats = await mongo_service.get_week_stats(user.telegram_id)
                    
                    if not week_stats or week_stats[0] == 0:
                        continue  # Skip if no tasks completed
                    
                    completed, total, avg_quality = week_stats
                    
                    lang = user.interface_language.value
                    achievement = self._get_achievement_message(avg_quality, completed, lang)
                    
                    message = get_text(lang, "weekly_report",
                                      completed=completed,
                                      total=total,
                                      quality=avg_quality,
                                      achievement=achievement)
                    
                    await self.bot.send_message(user.telegram_id, message)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send weekly report to {user.telegram_id}: {e}")
    
    def _get_motivation_message(self, quality: int, lang: str) -> str:
        """Get motivational message based on quality"""
        import random
        
        if lang == "uk":
            messages = {
                "excellent": [
                    "🏆 Відмінно! Ви володієте мовою на високому рівні!",
                    "🌟 Неймовірно! Ваша наполегливість вражає!",
                    "💎 Ви справжній діамант серед учнів!",
                    "🚀 Космічний результат! Так тримати!",
                ],
                "great": [
                    "💪 Чудові результати! Продовжуйте в тому ж дусі!",
                    "🎯 Влучно! Ваші зусилля дають плоди!",
                    "⭐ Ви на правильному шляху до майстерності!",
                    "🔥 Ви палаєте! Продовжуйте!",
                ],
                "good": [
                    "👍 Добре! Ще трохи практики і будете експертом!",
                    "📈 Прогрес очевидний! Не зупиняйтесь!",
                    "🌱 Ваші знання ростуть кожен день!",
                ],
                "keep_going": [
                    "💪 Не здавайтесь! Кожен день ви стаєте кращими!",
                    "🌈 Після труднощів завжди приходить успіх!",
                    "🎓 Навіть маленькі кроки ведуть до великої мети!",
                    "💫 Головне — не зупинятись!",
                ]
            }
            
            if quality >= 90:
                return random.choice(messages["excellent"])
            elif quality >= 75:
                return random.choice(messages["great"])
            elif quality >= 60:
                return random.choice(messages["good"])
            else:
                return random.choice(messages["keep_going"])
        else:  # ru
            messages = {
                "excellent": [
                    "🏆 Отлично! Вы владеете языком на высоком уровне!",
                    "🌟 Невероятно! Ваша настойчивость впечатляет!",
                    "💎 Вы настоящий бриллиант среди учеников!",
                    "🚀 Космический результат! Так держать!",
                ],
                "great": [
                    "💪 Отличные результаты! Продолжайте в том же духе!",
                    "🎯 В точку! Ваши усилия приносят плоды!",
                    "⭐ Вы на верном пути к мастерству!",
                    "🔥 Вы в огне! Продолжайте!",
                ],
                "good": [
                    "👍 Хорошо! Ещё немного практики и будете экспертом!",
                    "📈 Прогресс очевиден! Не останавливайтесь!",
                    "🌱 Ваши знания растут каждый день!",
                ],
                "keep_going": [
                    "💪 Не сдавайтесь! Каждый день вы становитесь лучше!",
                    "🌈 После трудностей всегда приходит успех!",
                    "🎓 Даже маленькие шаги ведут к большой цели!",
                    "💫 Главное — не останавливаться!",
                ]
            }
            
            if quality >= 90:
                return random.choice(messages["excellent"])
            elif quality >= 75:
                return random.choice(messages["great"])
            elif quality >= 60:
                return random.choice(messages["good"])
            else:
                return random.choice(messages["keep_going"])
    
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
