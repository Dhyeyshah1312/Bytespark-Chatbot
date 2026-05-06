from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

# CONFIG
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), "credentials.json")


def schedule_meeting(name, email):
    try:
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
Your meeting has been scheduled!

Name: {name}
Email: {email}

Check your calendar for details.

Join Meeting:
{meet_link}
"""

    except Exception as e:
        print("ERROR:", e)  # Debug in terminal
        return f"Failed to schedule meeting: {str(e)}"
