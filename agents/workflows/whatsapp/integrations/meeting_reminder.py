"""
Meeting reminder integration for WhatsApp workflow.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository
from .google_calendar import google_calendar
from .whatsapp import send_whatsapp_message
from .perplexity_search import PerplexitySearchTool
from ..memory import WhatsAppMemoryManager


class MeetingReminder:
    """Meeting reminder integration."""

    def __init__(self):
        """Initialize meeting reminder integration."""
        self.reminder_minutes = 15  # Send reminder 15 minutes before meeting
        self.perplexity_tool = PerplexitySearchTool()
        self.memory_manager = WhatsAppMemoryManager()

    def _get_user_context(self, user_id: str) -> str:
        """Get user's professional context from memories."""
        try:
            # Search for professional context in memories
            professional_queries = [
                "work job role company profession career",
                "skills expertise experience background",
                "industry business interests projects"
            ]

            all_memories = []
            for query in professional_queries:
                memories = self.memory_manager.search_memories(query, user_id, limit=3)
                if memories:
                    for memory in memories:
                        memory_text = memory.get("memory", str(memory))
                        if memory_text not in all_memories:
                            all_memories.append(memory_text)

            if all_memories:
                return "\n".join(all_memories[:5])  # Limit to top 5 memories
            return ""
        except Exception as e:
            logger.error(f"Error retrieving user context: {str(e)}")
            return ""

    def _format_meeting_summary(self, event: Dict[str, Any], user_id: str) -> str:
        """Format meeting summary for WhatsApp message."""
        try:
            # Extract event details
            summary = event.get("summary", "Untitled Meeting")
            description = event.get("description", "No description provided")
            start_time = datetime.fromisoformat(
                event["start"]["dateTime"].replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(
                event["end"]["dateTime"].replace("Z", "+00:00")
            )
            attendees = event.get("attendees", [])

            # Get user's context from memories
            user_context = self._get_user_context(user_id)

            # Format the message
            message = f"""📅 *Meeting Reminder*

*{summary}*

⏰ *Time:* {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}
📅 *Date:* {start_time.strftime('%B %d, %Y')}

📝 *Agenda:*
{description}

👥 *Attendees:*
"""
            # Add attendees with their profiles and potential connection points
            for i, attendee in enumerate(attendees[:5]):  # Only process top 5 attendees
                name = attendee.get("displayName", attendee.get("email", "Unknown"))
                message += f"• {name}\n"
                
                # Get attendee profile using Perplexity
                try:
                    profile = self.perplexity_tool._search_with_perplexity(
                        self.perplexity_tool._format_search_query(name)
                    )
                    # Add a brief profile summary (first 2-3 sentences)
                    profile_summary = " ".join(profile.split(". ")[:2]) + "."
                    message += f"  _Profile:_ {profile_summary}\n"

                    # Generate personalized connection points if user context exists
                    if user_context:
                        try:
                            connection_prompt = f"""Based on the following information, suggest specific connection points or ice breakers:

YOUR BACKGROUND:
{user_context}

PERSON TO CONNECT WITH:
{profile}

Please provide 1-2 specific connection points or conversation starters that could help establish rapport."""

                            connection_points = self.perplexity_tool._search_with_perplexity(connection_prompt)
                            message += f"  _Connection Points:_ {connection_points}\n\n"
                        except Exception as e:
                            logger.error(f"Error generating connection points: {str(e)}")
                            message += "\n"
                    else:
                        message += "\n"

                except Exception as e:
                    logger.error(f"Error getting profile for {name}: {str(e)}")
                    message += "  _Profile:_ Unable to fetch profile information\n\n"

            if len(attendees) > 5:
                message += f"\n... and {len(attendees) - 5} more attendees"

            return message

        except Exception as e:
            logger.error(f"Error formatting meeting summary: {str(e)}")
            return f"Meeting Reminder: {summary} at {start_time.strftime('%I:%M %p')}"

    async def check_upcoming_meetings(self, user_id: str) -> None:
        """Check for upcoming meetings and send reminders."""
        try:
            logger.info(f"Checking upcoming meetings for user: {user_id}")

            # Get user from database
            db = SessionLocal()
            repo = UserRepository(db)
            user = repo.get_user_by_id(user_id)
            db.close()

            if not user:
                logger.error(f"User not found: {user_id}")
                return

            # Get upcoming events
            result = google_calendar.list_events(user_id, max_results=10)
            if not result["success"]:
                logger.error(f"Failed to get calendar events: {result['error']}")
                return

            events = result["data"].get("items", [])
            now = datetime.now(timezone.utc)

            for event in events:
                try:
                    start_time = datetime.fromisoformat(
                        event["start"]["dateTime"].replace("Z", "+00:00")
                    )
                    time_until_meeting = start_time - now

                    # Check if meeting is starting in reminder_minutes
                    if timedelta(minutes=self.reminder_minutes - 1) <= time_until_meeting <= timedelta(
                        minutes=self.reminder_minutes + 1
                    ):
                        # Format and send reminder
                        message = self._format_meeting_summary(event, user_id)
                        await send_whatsapp_message(
                            {
                                "to": user.phoneNumber,
                                "type": "text",
                                "text": {"body": message},
                            }
                        )
                        logger.info(
                            f"Sent meeting reminder for event: {event.get('id')}",
                            user_id=user_id,
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing event {event.get('id')}: {str(e)}",
                        user_id=user_id,
                    )

        except Exception as e:
            logger.error(f"Error checking upcoming meetings: {str(e)}", user_id=user_id)


# Create and export the meeting_reminder instance
meeting_reminder = MeetingReminder() 