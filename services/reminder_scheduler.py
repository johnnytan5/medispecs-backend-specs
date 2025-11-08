"""
Reminder Scheduler Service - Foundation for executing reminders

This service will check reminders and execute them based on schedule.
Execution logic is not implemented yet - this is just the foundation.
"""

import asyncio
from datetime import datetime, time as dt_time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models import Reminder
from config import USER_ID, CHECK_INTERVAL_SECONDS, ENABLE_REMINDER_EXECUTION, DEBUG_SCHEDULER


class ReminderScheduler:
    """
    Scheduler to check and execute reminders based on time and frequency.
    
    Note: Execution logic is not implemented yet. This is the foundation.
    """
    
    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the reminder scheduler"""
        if not ENABLE_REMINDER_EXECUTION:
            print("⏸️  Reminder execution is disabled in config")
            return
        
        if self.is_running:
            print("⚠️  Scheduler is already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        
        # Display current time for verification
        now = datetime.now()
        print(f"▶️  Reminder scheduler started for user: {self.user_id}")
        print(f"⏰ Current system time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Current day: {now.strftime('%A')} (weekday: {now.weekday()})")
    
    async def stop(self):
        """Stop the reminder scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print("⏹️  Reminder scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop - checks reminders periodically"""
        while self.is_running:
            try:
                await self._check_and_execute_reminders()
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in scheduler loop: {e}")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    
    async def _check_and_execute_reminders(self):
        """
        Check for due reminders and execute them.
        Displays reminders on OLED screen when they are due.
        """
        async with AsyncSessionLocal() as db:
            # Get all reminders for the user
            from sqlalchemy import select
            stmt = select(Reminder).where(Reminder.user_id == self.user_id)
            result = await db.execute(stmt)
            reminders = result.scalars().all()
            
            now = datetime.now()
            current_time = now.time()
            current_day = now.weekday()  # 0=Monday, 6=Sunday
            
            # Log check activity (verbose for debugging)
            if DEBUG_SCHEDULER:
                print(f"⏰ [Scheduler Check] Time: {current_time.strftime('%H:%M:%S')}, Day: {current_day}, Reminders: {len(reminders)}")
            
            if not reminders:
                if DEBUG_SCHEDULER:
                    print(f"   ⚠️  No reminders in database to check")
                return
            
            for reminder in reminders:
                if self._is_reminder_due(reminder, current_time, current_day):
                    print(f"🔔 Reminder due: {reminder.title} (ID: {reminder.reminder_id})")
                    
                    # Format message for display
                    display_message = reminder.title.upper()
                    if reminder.time_of_day:
                        display_message = f"{reminder.time_of_day} {display_message}"
                    
                    # Speak reminder FIRST (immediate, no delay!)
                    try:
                        from services.tts_service import get_tts_service
                        from config import TTS_ENABLED, TTS_SPEAK_REMINDERS
                        
                        if TTS_ENABLED and TTS_SPEAK_REMINDERS:
                            tts = get_tts_service()
                            if tts.is_available:
                                # Just speak the reminder title/task (not the time)
                                await tts.speak_async(reminder.title)
                    except Exception as e:
                        print(f"❌ Error speaking reminder: {e}")
                    
                    # Display on OLED (fire-and-forget, runs in background for 10s)
                    try:
                        from services.oled_display import get_oled_service
                        import asyncio
                        
                        oled = get_oled_service()
                        
                        # Print what's being displayed on OLED
                        print(f"// OLED// {display_message} //OLED//")
                        
                        # Run OLED display in background (doesn't block)
                        asyncio.create_task(
                            asyncio.to_thread(
                                oled.display_reminder,
                                message=display_message,
                                font_size=14,
                                should_blink=True,
                                display_time=10
                            )
                        )
                    except Exception as e:
                        print(f"❌ Error displaying reminder on OLED: {e}")
                    
                    # Additional actions can be added here:
                    # - Send push notification
                    # - Log the execution
    
    def _is_reminder_due(
        self, reminder: Reminder, current_time: dt_time, current_day: int
    ) -> bool:
        """
        Check if a reminder is due based on its schedule.
        
        Args:
            reminder: The reminder to check
            current_time: Current time of day
            current_day: Current day of week (0=Monday, 6=Sunday)
        
        Returns:
            True if reminder should be executed now
        """
        # If no time specified, skip
        if not reminder.time_of_day:
            return False
        
        # Parse the reminder time (HH:MM format)
        try:
            hour, minute = map(int, reminder.time_of_day.split(':'))
            reminder_time = dt_time(hour, minute)
        except (ValueError, AttributeError):
            return False
        
        # Check if current time matches reminder time (within the check interval)
        # Simple approach: check if we're within the same minute
        time_matches = (
            current_time.hour == reminder_time.hour and
            current_time.minute == reminder_time.minute
        )
        
        if not time_matches:
            return False
        
        # Check schedule type
        if reminder.schedule_type == "daily":
            return True
        
        elif reminder.schedule_type == "weekly":
            # Convert: Python weekday (0=Mon) to reminder format (0=Sun)
            reminder_day = (current_day + 1) % 7
            return reminder_day in (reminder.days_of_week or [])
        
        return False
    
    async def get_upcoming_reminders(self, hours: int = 24) -> List[Reminder]:
        """
        Get reminders that are due in the next N hours.
        Useful for preview/display purposes.
        
        Args:
            hours: Number of hours to look ahead
        
        Returns:
            List of upcoming reminders
        """
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            stmt = select(Reminder).where(Reminder.user_id == self.user_id)
            result = await db.execute(stmt)
            reminders = result.scalars().all()
            
            # TODO: Implement proper upcoming reminder logic
            # For now, just return all reminders with time_of_day set
            upcoming = [r for r in reminders if r.time_of_day]
            return upcoming


# Global scheduler instance
_scheduler_instance: Optional[ReminderScheduler] = None


def get_scheduler() -> ReminderScheduler:
    """Get the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ReminderScheduler()
    return _scheduler_instance

