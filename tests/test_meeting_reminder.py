"""
Tests for meeting reminder functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from agents.workflows.whatsapp.integrations.meeting_reminder import MeetingReminder
from agents.workflows.whatsapp.tasks.meeting_reminder_task import MeetingReminderTask
from models.user_models import User, Account


@pytest.fixture
def meeting_reminder():
    """Create a MeetingReminder instance."""
    return MeetingReminder()


@pytest.fixture
def meeting_reminder_task():
    """Create a MeetingReminderTask instance."""
    return MeetingReminderTask()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        id="test_user_id",
        name="Test User",
        email="test@example.com",
        phoneNumber="+1234567890"
    )


@pytest.fixture
def mock_google_account():
    """Create a mock Google account."""
    return Account(
        id="test_account_id",
        accountId="test_google_id",
        providerId="google",
        userId="test_user_id",
        accessToken="test_access_token",
        refreshToken="test_refresh_token"
    )


@pytest.fixture
def sample_calendar_event():
    """Create a sample calendar event."""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(minutes=15)  # 15 minutes from now
    end_time = start_time + timedelta(hours=1)
    
    return {
        "id": "test_event_id",
        "summary": "Test Meeting",
        "description": "This is a test meeting",
        "start": {
            "dateTime": start_time.isoformat()
        },
        "end": {
            "dateTime": end_time.isoformat()
        },
        "attendees": [
            {
                "email": "attendee1@example.com",
                "displayName": "Attendee One"
            },
            {
                "email": "attendee2@example.com",
                "displayName": "Attendee Two"
            }
        ]
    }


def test_format_meeting_summary(meeting_reminder, sample_calendar_event):
    """Test formatting of meeting summary message."""
    summary = meeting_reminder._format_meeting_summary(sample_calendar_event)
    
    # Check that all important components are in the message
    assert "📅 *Meeting Reminder*" in summary
    assert "*Test Meeting*" in summary
    assert "⏰ Time:" in summary
    assert "📝 *Agenda:*" in summary
    assert "This is a test meeting" in summary
    assert "👥 *Attendees:*" in summary
    assert "• Attendee One" in summary
    assert "• Attendee Two" in summary


@pytest.mark.asyncio
async def test_check_upcoming_meetings(meeting_reminder, mock_user, sample_calendar_event):
    """Test checking upcoming meetings."""
    # Mock the database session and repository
    with patch('agents.workflows.whatsapp.integrations.meeting_reminder.SessionLocal') as mock_session, \
         patch('agents.workflows.whatsapp.integrations.meeting_reminder.UserRepository') as mock_repo_class, \
         patch('agents.workflows.whatsapp.integrations.meeting_reminder.google_calendar._make_request') as mock_calendar_request, \
         patch('agents.workflows.whatsapp.integrations.meeting_reminder.send_whatsapp_message') as mock_send_message:
        
        # Setup mocks
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_user_by_id.return_value = mock_user
        
        mock_calendar_request.return_value = {
            "success": True,
            "data": {
                "items": [sample_calendar_event]
            }
        }
        
        # Call the function
        await meeting_reminder.check_upcoming_meetings(mock_user.id)
        
        # Verify that WhatsApp message was sent
        mock_send_message.assert_called_once()
        message_payload = mock_send_message.call_args[0][0]
        assert message_payload["to"] == mock_user.phoneNumber
        assert message_payload["type"] == "text"
        assert "Test Meeting" in message_payload["text"]["body"]


@pytest.mark.asyncio
async def test_meeting_reminder_task(meeting_reminder_task):
    """Test the meeting reminder task."""
    # Mock the database session and repository
    with patch('agents.workflows.whatsapp.tasks.meeting_reminder_task.SessionLocal') as mock_session, \
         patch('agents.workflows.whatsapp.tasks.meeting_reminder_task.UserRepository') as mock_repo_class, \
         patch('agents.workflows.whatsapp.tasks.meeting_reminder_task.meeting_reminder.check_upcoming_meetings') as mock_check_meetings:
        
        # Setup mocks
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_users_with_google_token.return_value = [
            User(id="user1", phoneNumber="+1234567890"),
            User(id="user2", phoneNumber="+0987654321")
        ]
        
        # Start the task
        meeting_reminder_task.start()
        
        # Wait for one iteration
        await asyncio.sleep(0.1)
        
        # Stop the task
        meeting_reminder_task.stop()
        
        # Verify that check_upcoming_meetings was called for each user
        assert mock_check_meetings.call_count == 2
        mock_check_meetings.assert_any_call("user1")
        mock_check_meetings.assert_any_call("user2")