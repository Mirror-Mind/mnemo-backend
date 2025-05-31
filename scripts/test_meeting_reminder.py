"""
Script to manually test the meeting reminder functionality.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from agents.workflows.whatsapp.integrations.meeting_reminder import meeting_reminder
from agents.workflows.whatsapp.tasks.meeting_reminder_task import meeting_reminder_task
from models.user_models import SessionLocal
from repository.user_repository import UserRepository


async def test_single_user():
    """Test meeting reminder for a single user."""
    # Load environment variables
    load_dotenv()
    
    # Get test user ID from environment variable
    test_user_id = os.getenv("TEST_USER_ID")
    if not test_user_id:
        print("Error: TEST_USER_ID environment variable not set")
        return
    
    print(f"Testing meeting reminder for user: {test_user_id}")
    
    # Check upcoming meetings
    await meeting_reminder.check_upcoming_meetings(test_user_id)
    print("Meeting check completed")


async def test_background_task():
    """Test the background task for multiple users."""
    # Load environment variables
    load_dotenv()
    
    print("Starting meeting reminder task...")
    meeting_reminder_task.start()
    
    try:
        # Run for 2 minutes
        print("Task will run for 2 minutes...")
        await asyncio.sleep(120)
    except KeyboardInterrupt:
        print("\nStopping task...")
    finally:
        meeting_reminder_task.stop()
        print("Task stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test meeting reminder functionality")
    parser.add_argument(
        "--mode",
        choices=["single", "background"],
        default="single",
        help="Test mode: single user or background task"
    )
    
    args = parser.parse_args()
    
    if args.mode == "single":
        asyncio.run(test_single_user())
    else:
        asyncio.run(test_background_task())