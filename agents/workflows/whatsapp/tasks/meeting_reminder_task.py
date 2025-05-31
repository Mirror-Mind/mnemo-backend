"""
Background task for checking and sending meeting reminders.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository
from ..integrations.meeting_reminder import meeting_reminder


class MeetingReminderTask:
    """Background task for meeting reminders."""

    def __init__(self):
        """Initialize the reminder task."""
        self.check_interval = 60  # Check every minute
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

    async def _get_active_users(self) -> List[str]:
        """Get list of users with connected Google Calendar."""
        try:
            db = SessionLocal()
            repo = UserRepository(db)
            users = repo.get_users_with_google_token()
            user_ids = [user.id for user in users]
            return user_ids
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            return []
        finally:
            if db:
                db.close()

    async def _check_meetings(self):
        """Check for upcoming meetings for all active users."""
        while self.is_running:
            try:
                # Get active users
                user_ids = await self._get_active_users()
                
                # Check meetings for each user
                for user_id in user_ids:
                    await meeting_reminder.check_upcoming_meetings(user_id)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in meeting check task: {str(e)}")
                await asyncio.sleep(self.check_interval)

    def start(self):
        """Start the reminder task."""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._check_meetings())
            logger.info("Meeting reminder task started")

    def stop(self):
        """Stop the reminder task."""
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
            logger.info("Meeting reminder task stopped")


# Initialize the task
meeting_reminder_task = MeetingReminderTask()