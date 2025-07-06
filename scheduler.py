"""
Discord Slowmode Bot - Scheduler Module
"""

import logging
import asyncio
from datetime import datetime, time
from typing import Dict, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

class SlowmodeScheduler:
    """Handles scheduling of slowmode changes"""
    
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.schedules: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Slowmode scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            
    async def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Slowmode scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            
    async def add_schedule(self, schedule_id: str, channel_id: int, 
                         start_time: str, end_time: str, 
                         slowmode_seconds: int = 30, timezone: str = 'UTC',
                         days: list = None, restore_seconds: int = 0) -> bool:
        """Add a new slowmode schedule
        
        Args:
            schedule_id: Unique identifier for the schedule
            channel_id: Discord channel ID
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            slowmode_seconds: Slowmode duration in seconds
            timezone: Timezone for the schedule
            days: List of days to run (mon, tue, wed, thu, fri, sat, sun)
            restore_seconds: Slowmode to restore to after schedule ends
            
        Returns:
            True if schedule was added successfully, False otherwise
        """
        try:
            # Parse time strings
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            # Validate time format
            if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
                logger.error(f"Invalid start time format: {start_time}")
                return False
                
            if not (0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                logger.error(f"Invalid end time format: {end_time}")
                return False
                
            # Get timezone
            tz = pytz.timezone(timezone)
            
            # Default to all days if not specified
            if days is None:
                days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            
            # Store schedule data
            self.schedules[schedule_id] = {
                'channel_id': channel_id,
                'start_time': start_time,
                'end_time': end_time,
                'slowmode_seconds': slowmode_seconds,
                'timezone': timezone,
                'days': days,
                'restore_seconds': restore_seconds
            }
            
            # Convert days to cron format
            day_of_week = ','.join([str(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].index(day)) for day in days])
            
            # Add start job (enable slowmode)
            start_job_id = f"{schedule_id}_start"
            self.scheduler.add_job(
                func=self._enable_slowmode,
                trigger=CronTrigger(
                    hour=start_hour,
                    minute=start_minute,
                    day_of_week=day_of_week,
                    timezone=tz
                ),
                args=[channel_id, slowmode_seconds],
                id=start_job_id,
                replace_existing=True
            )
            
            # Add end job (restore original slowmode)
            end_job_id = f"{schedule_id}_end"
            self.scheduler.add_job(
                func=self._restore_slowmode,
                trigger=CronTrigger(
                    hour=end_hour,
                    minute=end_minute,
                    day_of_week=day_of_week,
                    timezone=tz
                ),
                args=[channel_id, restore_seconds],
                id=end_job_id,
                replace_existing=True
            )
            
            logger.info(f"Added slowmode schedule {schedule_id}: "
                       f"Channel {channel_id}, {start_time}-{end_time} "
                       f"({slowmode_seconds}s slowmode)")
            
            return True
            
        except ValueError as e:
            logger.error(f"Invalid time format for schedule {schedule_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to add schedule {schedule_id}: {e}")
            return False
            
    async def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a slowmode schedule
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            True if schedule was removed successfully, False otherwise
        """
        try:
            if schedule_id not in self.schedules:
                logger.warning(f"Schedule {schedule_id} not found")
                return False
                
            # Remove jobs
            start_job_id = f"{schedule_id}_start"
            end_job_id = f"{schedule_id}_end"
            
            try:
                self.scheduler.remove_job(start_job_id)
            except Exception as e:
                logger.warning(f"Failed to remove start job {start_job_id}: {e}")
                
            try:
                self.scheduler.remove_job(end_job_id)
            except Exception as e:
                logger.warning(f"Failed to remove end job {end_job_id}: {e}")
                
            # Remove from schedules
            del self.schedules[schedule_id]
            
            logger.info(f"Removed slowmode schedule {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove schedule {schedule_id}: {e}")
            return False
            
    def get_guild_schedules(self, guild_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all schedules for a specific guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary of schedules for the guild
        """
        guild_schedules = {}
        
        for schedule_id, schedule_data in self.schedules.items():
            # Check if schedule belongs to this guild
            if schedule_id.startswith(f"{guild_id}_"):
                guild_schedules[schedule_id] = schedule_data
                
        return guild_schedules
        
    async def _enable_slowmode(self, channel_id: int, slowmode_seconds: int):
        """Enable slowmode for a channel"""
        try:
            if hasattr(self.bot, 'set_channel_slowmode'):
                success = await self.bot.set_channel_slowmode(channel_id, slowmode_seconds)
            else:
                # Fallback for function-based approach
                success = await set_channel_slowmode(channel_id, slowmode_seconds)
            
            if success:
                logger.info(f"Enabled {slowmode_seconds}s slowmode for channel {channel_id}")
            else:
                logger.error(f"Failed to enable slowmode for channel {channel_id}")
                
        except Exception as e:
            logger.error(f"Error enabling slowmode for channel {channel_id}: {e}")
            
    async def _disable_slowmode(self, channel_id: int):
        """Disable slowmode for a channel"""
        try:
            success = await self.bot.set_channel_slowmode(channel_id, 0)
            
            if success:
                logger.info(f"Disabled slowmode for channel {channel_id}")
            else:
                logger.error(f"Failed to disable slowmode for channel {channel_id}")
                
        except Exception as e:
            logger.error(f"Error disabling slowmode for channel {channel_id}: {e}")
    
    async def _restore_slowmode(self, channel_id: int, restore_seconds: int):
        """Restore slowmode to original setting for a channel"""
        try:
            success = await self.bot.set_channel_slowmode(channel_id, restore_seconds)
            
            if success:
                slowmode_text = f"{restore_seconds} seconds" if restore_seconds > 0 else "disabled"
                logger.info(f"Restored slowmode to {slowmode_text} for channel {channel_id}")
            else:
                logger.error(f"Failed to restore slowmode for channel {channel_id}")
                
        except Exception as e:
            logger.error(f"Error restoring slowmode for channel {channel_id}: {e}")
            
    def get_next_run_times(self, schedule_id: str) -> Dict[str, Optional[datetime]]:
        """Get the next run times for a schedule
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            Dictionary with next start and end times
        """
        try:
            start_job_id = f"{schedule_id}_start"
            end_job_id = f"{schedule_id}_end"
            
            start_job = self.scheduler.get_job(start_job_id)
            end_job = self.scheduler.get_job(end_job_id)
            
            return {
                'next_start': start_job.next_run_time if start_job else None,
                'next_end': end_job.next_run_time if end_job else None
            }
            
        except Exception as e:
            logger.error(f"Error getting next run times for schedule {schedule_id}: {e}")
            return {'next_start': None, 'next_end': None}
