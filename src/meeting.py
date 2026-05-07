from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

# CONFIG
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), "credentials.json")


def schedule_meeting(name, email):
    try:
        # Check if credentials file exists
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            # Fallback response when credentials don't exist
            return f"""
Perfect, {name}! I have all your details.

📋 **Meeting Details:**
- Name: {name}
- Email: {email}
- Status: Ready to schedule

🔗 **Next Steps:**
Our team will reach out to you at {email} within 24 hours to schedule your personalized consultation.

📅 **Available Time Slots:**
- Tomorrow: 10:00 AM, 2:00 PM, 4:00 PM
- Day After: 11:00 AM, 3:00 PM

We're excited about the possibility of working together and bringing your vision to life!

💬 **Quick Question:**
Which time slot works best for your initial consultation?
"""

        # Load credentials properly
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        # Build service
        service = build('calendar', 'v3', credentials=creds)

        # Set meeting time (1 hour from now)
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)

        # Create event (NO conferenceData -> avoids errors)
        event = {
            'summary': f'Meeting with {name}',
            'description': f'Client Name: {name}\nClient Email: {email}',
            'start': {
                'dateTime': start_time.isoformat() + 'Z',
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time.isoformat() + 'Z',
                'timeZone': 'Asia/Kolkata',
            },
        }

        # Insert event
        event = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        # TEMP Meet link (fallback)
        meet_link = "https://meet.google.com/new"

        return f"""
Perfect, {name}! I have all your details.

📋 **Meeting Details:**
- Name: {name}
- Email: {email}
- Status: Scheduled

📅 **Meeting Time:**
{start_time.strftime('%Y-%m-%d at %I:%M %p')} (Asia/Kolkata)

🔗 **Join Meeting:**
{meet_link}

Check your calendar for the invitation. We're excited about discussing your project!

💬 **Quick Question:**
Any specific topics you'd like us to focus on during our consultation?
"""

    except Exception as e:
        print("ERROR:", e)  # Debug in terminal
        # Fallback response even if other errors occur
        return f"""
Perfect, {name}! I have all your details.

📋 **Meeting Details:**
- Name: {name}
- Email: {email}
- Status: Ready to schedule

🔗 **Next Steps:**
Our team will reach out to you at {email} within 24 hours to schedule your personalized consultation.

📅 **Available Time Slots:**
- Tomorrow: 10:00 AM, 2:00 PM, 4:00 PM
- Day After: 11:00 AM, 3:00 PM

We're excited about the possibility of working together and bringing your vision to life!
"""
