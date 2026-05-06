import datetime
import os.path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = None

    # Load saved login
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save login token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def create_meeting(name, email):
    service = get_calendar_service()

    start = datetime.datetime.now() + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(hours=1)

    event = {
        'summary': f'Meeting with {name}',
        'description': 'Discussion with ByteSpark team',
        'start': {
            'dateTime': start.isoformat(),
            'timeZone': 'Asia/Kolkata'
        },
        'end': {
            'dateTime': end.isoformat(),
            'timeZone': 'Asia/Kolkata'
        },
        'attendees': [
            {'email': email}
        ],
        'conferenceData': {
            'createRequest': {
                'requestId': 'bytespark-meet',
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        }
    }

    event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    return event.get("hangoutLink")