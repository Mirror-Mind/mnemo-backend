"""
Script to test sending WhatsApp messages with meeting summaries.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from agents.workflows.whatsapp.integrations.whatsapp import send_whatsapp_message


async def test_meeting_summary():
    """Test sending a meeting summary via WhatsApp."""
    # Load environment variables
    load_dotenv()
    
    # Get test phone number from environment
    test_phone = os.getenv("TEST_WHATSAPP_NUMBER")
    if not test_phone:
        print("Error: TEST_WHATSAPP_NUMBER environment variable not set")
        return
    
    # Create a sample meeting summary
    now = datetime.now(timezone.utc)
    meeting_time = now + timedelta(hours=1)
    
    message = f"""📅 *Meeting Reminder*

*Project Review Meeting*

⏰ *Time:* {meeting_time.strftime('%I:%M %p')} - {(meeting_time + timedelta(hours=1)).strftime('%I:%M %p')}
📅 *Date:* {meeting_time.strftime('%B %d, %Y')}

📝 *Agenda:*
1. Review project progress
2. Discuss technical challenges
3. Plan next sprint
4. Q&A session

👥 *Attendees:*
• John Doe (Project Manager)
• Jane Smith (Tech Lead)
• Alice Johnson (Developer)
• Bob Wilson (Designer)

Please come prepared with your updates and questions.
"""

    # Prepare message payload
    payload = {
        "to": test_phone,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    print(f"Sending message to {test_phone}...")
    
    # Send the message
    success = await send_whatsapp_message(payload)
    
    if success:
        print("Message sent successfully!")
    else:
        print("Failed to send message. Check the logs for details.")


if __name__ == "__main__":
    asyncio.run(test_meeting_summary()) 