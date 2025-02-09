import base64
import json
from email.mime.text import MIMEText
from datetime import timezone
import pytz  # Import pytz for time zone support

from google_apis import create_service
from datetime import datetime, timedelta
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import re
from dateutil import parser
from googleapiclient.errors import HttpError
import pytz



CLIENT_SECRET = 'google_calender.json'
API_NAME = 'calendar'  # Corrected typo from 'calender' to 'calendar'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.send']

def construct_google_calendar_client(client_secret):
    """Constructs a Google Calendar API client."""
    try:
        service = create_service(client_secret, API_NAME, API_VERSION, SCOPES)
        return service
    except Exception as e:
        print(f"Failed to create service instance for {API_NAME}: {e}")
        return None

# Initialize the BERT model for NER
tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

class EventExtractor:
    def __init__(self):
        self.calendar_service = construct_google_calendar_client(CLIENT_SECRET)
        if self.calendar_service is None:
            raise Exception("Failed to initialize Google Calendar service.")

    def extract_time(self, text):
        """Extract time information from text using regex and dateutil."""
        # Common time patterns
        time_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
            r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)',  # 12-hour format
            r'\d{1,2}(?::|.)?\d{2}\s*(?:hrs?|hours?)',  # 24-hour format
            r'today at \d{1,2}(?::|.)?\d{2}',  # relative time
            r'tomorrow at \d{1,2}(?::|.)?\d{2}'  # relative time
        ]

        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    time_str = match.group()
                    print(f"Extracted time: {time_str}")
                    return parser.parse(time_str)
                except ValueError:
                    continue
        print("No time extracted from text.")
        return None
    def extract_duration(self, text):
        """Extract duration information from text."""
        duration_patterns = [
            (r'(\d+)\s*hours?', 'hours'),
            (r'(\d+)\s*mins?(?:utes?)?', 'minutes'),
            (r'(\d+)\s*hr', 'hours')
        ]

        for pattern, unit in duration_patterns:
            match = re.search(pattern, text)
            if match:
                value = int(match.group(1))
                if unit == 'hours':
                    return value
                elif unit == 'minutes':
                    return value / 60
        return 1  # default duration: 1 hour

    def extract_location(self, text):
        """Extract location information from text."""
        location_indicators = ['at', 'in', 'on']
        for indicator in location_indicators:
            pattern = f"{indicator} ([^.,!?]*)"
            match = re.search(pattern, text.lower())
            if match:
                location = match.group(1).strip()
                if not any(time_word in location.lower() for time_word in ['am', 'pm', 'hours', 'tomorrow', 'today']):
                    return location
        return "No location specified"

    def extract_event_details(self, prompt):
        """Extract all event details from the prompt using BERT NER and regex."""
        # Use BERT NER to extract entities
        entities = ner(prompt)

        # Initialize default values
        event_details = {
            'summary': None,
            'location': None,
            'description': prompt,  # Use full prompt as description
            'start_time': None,
            'duration_hours': None
        }

        # Extract event summary (look for sequences of words not tagged as other entities)
        words = prompt.split()
        summary_words = []
        for word in words:
            if not any(entity['word'] in word for entity in entities):
                summary_words.append(word)
        if summary_words:
            event_details['summary'] = ' '.join(summary_words[:5])  # Use first 5 untagged words as summary

        # Extract location
        event_details['location'] = self.extract_location(prompt)

        # Extract time
        start_time = self.extract_time(prompt)
        if start_time:
            event_details['start_time'] = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            # Default to tomorrow at 10 AM if no time specified
            tomorrow = datetime.now() + timedelta(days=1)
            tomorrow = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
            event_details['start_time'] = tomorrow.strftime("%Y-%m-%dT%H:%M:%S")

        # Extract duration
        event_details['duration_hours'] = self.extract_duration(prompt)

        return event_details

    def check_existing_event(self, start_time, end_time):
        """Check if an event already exists at the specified time."""
        try:
            # Convert start_time and end_time to the calendar's time zone
            time_zone = pytz.timezone('Asia/Kolkata') # Update this to match your calendar's time zone
            time_min = (start_time - timedelta(minutes=1)).astimezone(time_zone).isoformat()
            time_max = (end_time + timedelta(minutes=1)).astimezone(time_zone).isoformat()

            print(f"Checking for events between {time_min} and {time_max}")

            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            print(f"Found {len(events)} existing events.")
            return len(events) > 0  # Return True if there are existing events
        except HttpError as error:
            print(f"An error occurred while checking for existing events: {error}")
            return False
    def send_reply_email(self, sender_email, subject, body):
        """Send a reply email to the sender."""
        try:
            service = create_service(CLIENT_SECRET, 'gmail', 'v1', SCOPES)
            message = MIMEText(body)
            message['to'] = sender_email
            message['subject'] = f"Re: {subject}"
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            sent_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            return f"Reply email sent successfully! Message ID: {sent_message['id']}"
        except Exception as e:
            return f"Error sending reply email: {str(e)}"

    def create_calendar_event(self, event_details, sender_email=None, subject=None):
        """Create a calendar event using the extracted details."""
        try:
            # Use the primary calendar (default calendar for the authenticated user)
            calendar_id = 'primary'

            # Parse the start time and calculate the end time
            start_datetime = datetime.strptime(event_details['start_time'], "%Y-%m-%dT%H:%M:%S")
            end_datetime = start_datetime + timedelta(hours=event_details['duration_hours'])

            # Check if an event already exists at the specified time
            if self.check_existing_event(start_datetime, end_datetime):
                if sender_email and subject:
                    # Send a reply email to the sender
                    reply_body = (
                        f"Hi,\n\n"
                        f"An event already exists at the specified time ({start_datetime.strftime('%Y-%m-%d %H:%M')}).\n"
                        f"Please choose a different time.\n\n"
                        f"Best regards,\nYour Calendar Assistant"
                    )
                    reply_result = self.send_reply_email(sender_email, subject, reply_body)
                    return reply_result
                else:
                    return "An event already exists at the specified time."

            # Define the event body
            event_body = {
                'summary': event_details['summary'],
                'location': event_details['location'],
                'description': event_details['description'],
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Kolkata'
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Kolkata'
                }
            }

            # Insert the event into the calendar
            event = self.calendar_service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return f"Event created successfully! Link: {event.get('htmlLink')}"

        except HttpError as error:
            return f"An error occurred: {error}"
        except Exception as e:
            return f"Error creating event: {str(e)}"

