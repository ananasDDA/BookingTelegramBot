from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
from datetime import datetime, timedelta
import socket
import ssl
from time import sleep
import logging
import os
from dotenv import load_dotenv
from telebot import TeleBot

logger = logging.getLogger(__name__)

# Update scope to allow writing to calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']  # Remove .readonly

load_dotenv()

class GoogleCalendarHelper:
    def __init__(self):
        self.creds = None
        self.service = None
        # Define calendar IDs for each sport using environment variables
        self.calendar_ids = {
            'Бадминтон': os.getenv('BADMINTON_CALENDAR_ID'),
            'Сквош': os.getenv('SQUASH_CALENDAR_ID')
        }
        self.setup_credentials()

    def delete_token(self):
        """Delete the existing token.pickle file if it exists."""
        try:
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
                print("Existing token.pickle file deleted.")
        except Exception as e:
            print(f"Error deleting token.pickle: {e}")

    def setup_credentials(self):
        try:
            # Delete existing token first
            self.delete_token()

            # Load or create credentials
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)

                    # Get authorization URL before running local server
                    auth_url = flow.authorization_url()[0]

                    # Send authorization URL to Telegram channel
                    bot = TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
                    bot.send_message(
                        os.getenv('LOGS_CHANNEL_ID'),
                        f"🔐 *Google Calendar Authorization Required*\n\n"
                        f"Please authorize the application using this link:\n\n"
                        f"`{auth_url}`\n\n"
                        f"⚠️ _This link will expire after first use_",
                        parse_mode='Markdown'
                    )

                    self.creds = flow.run_local_server(port=8080)

                with open('token.pickle', 'wb') as token:
                    pickle.dump(self.creds, token)

            self.service = build('calendar', 'v3', credentials=self.creds)

        except Exception as e:
            logger.error(f"Error in setup_credentials: {str(e)}")
            raise

    def get_calendar_id(self, sport):
        """Get calendar ID for specific sport"""
        return self.calendar_ids.get(sport)

    def get_busy_slots(self, date, sport):
        max_retries = 3
        retry_count = 0
        calendar_id = self.get_calendar_id(sport)

        if not calendar_id:
            logger.error(f"No calendar ID found for sport: {sport}")
            return []

        while retry_count < max_retries:
            try:
                start_time = datetime.combine(date, datetime.min.time())
                end_time = datetime.combine(date, datetime.max.time())

                start_time_str = start_time.isoformat() + 'Z'
                end_time_str = end_time.isoformat() + 'Z'

                # Get busy slots from specified calendar
                events_result = self.service.events().list(
                    calendarId=calendar_id,  # Use sport-specific calendar
                    timeMin=start_time_str,
                    timeMax=end_time_str,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])
                busy_slots = []

                for event in events:
                    start = event['start'].get('dateTime')
                    end = event['end'].get('dateTime')
                    if start and end:  # Only include events with specific times
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                        busy_slots.append({
                            'start': start_dt,
                            'end': end_dt,
                            'hour': start_dt.hour
                        })

                return busy_slots

            except (socket.error, ssl.SSLError) as e:
                retry_count += 1
                if retry_count == max_retries:
                    print(f"Failed after {max_retries} retries: {e}")
                    return []
                sleep(1)

            except Exception as e:
                print(f"Unexpected error: {e}")
                return []

    def create_event(self, event_data, sport):
        """Create a new event in the sport-specific calendar."""
        try:
            calendar_id = self.get_calendar_id(sport)
            if not calendar_id:
                raise ValueError(f"No calendar ID found for sport: {sport}")

            logger.info(f"Creating event in {sport} calendar")
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()

            logger.info(f"Event created successfully in {sport} calendar: {event.get('id')}")
            return event

        except Exception as e:
            logger.error(f"Error creating event in {sport} calendar: {str(e)}")
            raise