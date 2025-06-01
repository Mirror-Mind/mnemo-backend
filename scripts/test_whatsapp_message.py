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
from agents.workflows.whatsapp.integrations.perplexity_search import PerplexitySearchTool


async def get_attendee_profiles(attendees):
    """Get professional profiles for attendees using Perplexity."""
    profiles = []
    tool = PerplexitySearchTool()
    
    for attendee in attendees:
        name, role = attendee
        try:
            # Format search query
            query = f"{name} {role} professional background current role company work"
            # Get profile using Perplexity
            profile = tool._search_with_perplexity(query)
            profiles.append((name, role, profile))
        except Exception as e:
            print(f"Error getting profile for {name}: {str(e)}")
            # Add a basic profile if search fails
            profiles.append((name, role, f"Professional {role} with experience in the field."))
    
    return profiles


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
    
    # Define attendees with their roles
    attendees = [
        ("John Doe", "Project Manager"),
        ("Jane Smith", "Tech Lead"),
        ("Alice Johnson", "Developer"),
        ("Bob Wilson", "Designer")
    ]
    
    # Get attendee profiles
    print("Fetching attendee profiles...")
    attendee_profiles = await get_attendee_profiles(attendees)
    
    # Format the message with attendee profiles
    message = f"""📅 *Meeting Reminder*

*Project Review Meeting*

⏰ *Time:* {meeting_time.strftime('%I:%M %p')} - {(meeting_time + timedelta(hours=1)).strftime('%I:%M %p')}
📅 *Date:* {meeting_time.strftime('%B %d, %Y')}

📝 *Agenda:*
1. Review project progress
2. Discuss technical challenges
3. Plan next sprint
4. Q&A session

👥 *Attendees & Background:*
"""
    
    # Add attendee profiles
    for name, role, profile in attendee_profiles:
        message += f"\n*{name}* ({role}):\n"
        # Extract the most relevant parts of the profile
        profile_lines = profile.split('\n')
        for line in profile_lines[:3]:  # Take first 3 lines of profile
            if line.strip():
                message += f"• {line.strip()}\n"
    
    message += "\n🤝 *Common Connections:*\n"
    # Add some common connections based on profiles
    message += """• All team members have experience in agile development
• Shared background in enterprise software development
• Common interest in user-centered design
• Previous collaboration on similar projects"""

    message += "\n\nPlease come prepared with your updates and questions."

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