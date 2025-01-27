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
        # Define calendar IDs for each option
        self.calendar_ids = {
            'Бадминтон': os.getenv('FIRST_CALENDAR_ID'),
            'Сквош': os.getenv('SECOND_CALENDAR_ID')
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
            environment = os.getenv('ENVIRONMENT', 'local')
            logger.info(f"Running in {environment} environment")

            if environment == 'server':
                # Server mode: expect token.pickle to exist
                if not os.path.exists('token.pickle'):
                    raise FileNotFoundError(
                        "token.pickle not found. In server mode, this file must be "
                        "manually uploaded after being generated in local environment."
                    )
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)

                if not self.creds or not self.creds.valid:
                    if self.creds and self.creds.expired and self.creds.refresh_token:
                        self.creds.refresh(Request())
                    else:
                        raise ValueError(
                            "Invalid credentials in token.pickle. Please regenerate "
                            "in local environment and upload again."
                        )
            else:
                # Local mode: normal browser-based flow
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

                        # Save token for future use (and for server deployment)
                        with open('token.pickle', 'wb') as token:
                            pickle.dump(self.creds, token)
                        logger.info("New token.pickle file generated successfully")

            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Google Calendar service initialized successfully")

        except Exception as e:
            logger.error(f"Error in setup_credentials: {str(e)}")
            raise

    def get_calendar_id(self, option):
        """Get calendar ID for specific option"""
        return self.calendar_ids.get(option)

    def get_busy_slots(self, date, option):
        max_retries = 3
        retry_count = 0
        calendar_id = self.get_calendar_id(option)

        if not calendar_id:
            logger.error(f"No calendar ID found for option: {option}")
            return []

        while retry_count < max_retries:
            try:
                start_time = datetime.combine(date, datetime.min.time())
                end_time = datetime.combine(date, datetime.max.time())

                start_time_str = start_time.isoformat() + 'Z'
                end_time_str = end_time.isoformat() + 'Z'

                events_result = self.service.events().list(
                    calendarId=calendar_id,
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
                    if start and end:
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                        user_id = event.get('extendedProperties', {}).get('private', {}).get('userId')
                        busy_slots.append({
                            'start': start_dt,
                            'end': end_dt,
                            'hour': start_dt.hour,
                            'user_id': user_id
                        })

                return busy_slots

            except (socket.error, ssl.SSLError) as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    return []
                sleep(1)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return []

    def create_event(self, event_data, option):
        """Create a new event in the option-specific calendar."""
        try:
            calendar_id = self.get_calendar_id(option)
            if not calendar_id:
                raise ValueError(f"No calendar ID found for option: {option}")

            logger.info(f"Creating event in {option} calendar")
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()

            logger.info(f"Event created successfully in {option} calendar: {event.get('id')}")
            return event

        except Exception as e:
            logger.error(f"Error creating event in {option} calendar: {str(e)}")
            raise

    def get_month_bookings(self, start_date, end_date, option):
        """Get all bookings for a specific month"""
        calendar_id = self.get_calendar_id(option)
        if not calendar_id:
            return []

        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat() + 'T00:00:00Z',
                timeMax=end_date.isoformat() + 'T00:00:00Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            bookings = []
            for event in events_result.get('items', []):
                start = event['start'].get('dateTime')
                if start:
                    event_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
                    user_id = event.get('extendedProperties', {}).get('private', {}).get('userId')
                    bookings.append({
                        'date': event_date,
                        'user_id': user_id
                    })
            return bookings

        except Exception as e:
            logger.error(f"Error getting month bookings: {str(e)}")
            return []

    def get_user_bookings(self, start_date, end_date, option):
        """Get user's bookings for a specific month"""
        all_bookings = self.get_month_bookings(start_date, end_date, option)
        return [booking for booking in all_bookings if booking.get('user_id')]

    def get_user_bookings_for_date(self, date, option, user_id):
        """Get user's bookings for a specific date"""
        start_date = datetime.strptime(date, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=1)
        bookings = self.get_month_bookings(start_date, end_date, option)
        return [booking for booking in bookings if booking.get('user_id') == str(user_id)]