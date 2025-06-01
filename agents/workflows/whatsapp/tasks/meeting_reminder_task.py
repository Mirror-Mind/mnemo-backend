"""
Background task for checking and sending meeting reminders.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository
from ..integrations.google_calendar import google_calendar
from ..integrations.whatsapp import send_whatsapp_message
from ..integrations.meeting_reminder import meeting_reminder
import os


class MeetingReminderTask:
    """Background task for meeting reminders."""

    def __init__(self):
        """Initialize the reminder task."""
        self.check_interval = 3*60  # Check every 3minute
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.sent_reminders = {}  # {user_id: set(event_id)}
        self.server_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    async def _get_active_users(self) -> List[str]:
        """Get list of users with connected Google Calendar."""
        try:
            db = SessionLocal()
            repo = UserRepository(db)
            users = repo.get_users_with_google_token()
            user_ids = [str(user.id) for user in users]
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
                user_ids = await self._get_active_users()
                for user_id in user_ids:
                    if user_id not in self.sent_reminders:
                        self.sent_reminders[user_id] = set()
                    db = SessionLocal()
                    repo = UserRepository(db)
                    user = repo.get_user_by_id(user_id)
                    db.close()
                    if not user:
                        continue
                    result = google_calendar.list_events(user_id, max_results=10)
                    if not result["success"]:
                        continue
                    events = result["data"].get("items", [])
                    for event in events:
                        event_id = event.get("id")
                        if not event_id or event_id in self.sent_reminders[user_id]:
                            continue
                        start_time = datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00"))
                        time_until_meeting = start_time - datetime.now(start_time.tzinfo)
                        if timedelta(minutes=0) <= time_until_meeting <= timedelta(minutes=30):
                            message = meeting_reminder._format_meeting_summary(event)
                            # message += f"\n\n🟢 *Server Start Time:* {self.server_start_time}"
                            await send_whatsapp_message({
                                "to": os.getenv("TEST_WHATSAPP_NUMBER"),
                                "type": "text",
                                "text": {"body": message},
                            })
                            logger.info(f"Sent meeting reminder for event: {event_id}", user_id=user_id)
                            self.sent_reminders[user_id].add(event_id)
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