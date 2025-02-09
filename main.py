# import os
# import time
# import base64
# import google.generativeai as genai
# from google_apis import create_service
# from googleapiclient.errors import HttpError
# from email.mime.text import MIMEText
# from datetime import datetime, timedelta
# from collections import deque
# from time import sleep
# from calender import EventExtractor  # Import the EventExtractor class
#
#
# class RateLimiter:
#     def __init__(self, max_requests, time_window):
#         self.max_requests = max_requests
#         self.time_window = time_window  # in seconds
#         self.requests = deque()
#
#     def can_make_request(self):
#         now = datetime.now()
#         # Remove old requests
#         while self.requests and (now - self.requests[0]) > timedelta(seconds=self.time_window):
#             self.requests.popleft()
#
#         # Check if we can make a new request
#         if len(self.requests) < self.max_requests:
#             self.requests.append(now)
#             return True
#         return False
#
#     def wait_for_available_slot(self):
#         while not self.can_make_request():
#             sleep(1)  # Wait for 1 second before checking again
#
#
# def init_gmail_service(client_file, api_name='gmail', api_version='v1',
#                        scopes=['https://www.googleapis.com/auth/gmail.modify',
#                                'https://www.googleapis.com/auth/gmail.send',
#                                'https://www.googleapis.com/auth/gmail.readonly']):
#     return create_service(client_file, api_name, api_version, scopes)
#
#
# def _extract_body(payload):
#     body = '<Text body not available>'
#     if 'parts' in payload:
#         for part in payload['parts']:
#             if part['mimeType'] == 'text/plain' and 'data' in part['body']:
#                 body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
#                 break
#     elif 'body' in payload and 'data' in payload['body']:
#         body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
#     return body
#
#
# def get_latest_email(service, user_id='me'):
#     try:
#         result = service.users().messages().list(userId=user_id, maxResults=1, q="in:inbox").execute()
#         messages = result.get('messages', [])
#
#         if not messages:
#             return None
#
#         msg = messages[0]
#         msg_id = msg['id']
#         message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
#         payload = message['payload']
#         headers = payload.get('headers', [])
#
#         subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
#         sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'No sender')
#         date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'No date')
#         body = _extract_body(payload)
#
#         return {
#             'id': msg_id,
#             'subject': subject,
#             'sender': sender,
#             'date': date,
#             'body': body
#         }
#     except HttpError as error:
#         print(f'An error occurred: {error}')
#         return None
#
#
# def generate_email_response(email_body, rate_limiter):
#     try:
#         # Wait for an available slot in the rate limiter
#         rate_limiter.wait_for_available_slot()
#
#         genai.configure(api_key='AIzaSyDZdkCDQ9ugDLqmFkK0vzWZJUQdEi9cEaQ')
#         model = genai.GenerativeModel("gemini-pro")
#
#         prompt = f"""
#         Generate a professional email response based on this email content:
#         {email_body}
#
#         The response should:
#         1. Acknowledge the main points of the original email
#         2. Be professional and courteous
#         3. Provide relevant information or next steps
#         4. Keep the tone friendly but professional
#         """
#
#         response = model.generate_content(prompt)
#         return response.text if response else "I apologize, but I am unable to generate a response at this moment. Please try again later."
#     except Exception as e:
#         print(f"Error generating response: {e}")
#         return "I apologize, but I am unable to generate a response at this moment. Please try again later."
#
#
# def send_email(service, to, subject, body):
#     try:
#         message = MIMEText(body)
#         message['to'] = to
#         message['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
#         raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
#
#         sent_message = service.users().messages().send(
#             userId='me',
#             body={'raw': raw_message}
#         ).execute()
#
#         return sent_message
#     except Exception as e:
#         print(f"Error sending email: {e}")
#         return None
#
#
# def generate_email_summary(email_body):
#     genai.configure(api_key='AIzaSyDZdkCDQ9ugDLqmFkK0vzWZJUQdEi9cEaQ')
#     model = genai.GenerativeModel("gemini-pro")
#     response = model.generate_content(f"Summarize this email: {email_body}")
#     return response.text if response else "Summary not available."
#
#
# def monitor_new_emails(client_file):
#     service = init_gmail_service(client_file)
#     if not service:
#         print("Failed to initialize Gmail service.")
#         return
#
#     # Initialize rate limiter (60 requests per minute)
#     rate_limiter = RateLimiter(max_requests=60, time_window=60)
#
#     # Initialize EventExtractor for calendar functionality
#     event_extractor = EventExtractor()
#
#     last_processed_email_id = None
#
#     while True:
#         try:
#             print("Checking for new emails...")
#             email = get_latest_email(service)
#
#             if email and email['id'] != last_processed_email_id:
#                 print("\nNew Email Found:")
#                 print(f"From: {email['sender']}")
#                 print(f"Subject: {email['subject']}")
#                 print(f"Body: {email['body']}")
#                 print(f"Date: {email['date']}")
#
#                 # Generate email summary
#                 summary = generate_email_summary(email['body'])
#                 print(f"Summary: {summary}")
#
#                 # Extract event details from the email body
#                 event_details = event_extractor.extract_event_details(email['body'])
#                 print("\nExtracted Event Details:")
#                 for key, value in event_details.items():
#                     print(f"{key}: {value}")
#
#                 # Create a calendar event
#                 print("\nCreating calendar event...")
#                 event_result = event_extractor.create_calendar_event(event_details)
#                 print(event_result)
#
#                 # Generate and send email response
#                 response = generate_email_response(email['body'], rate_limiter)
#                 if response:
#                     print("\nSending response...")
#                     send_email(service, email['sender'], email['subject'], response)
#                     print("Response sent successfully!")
#
#                 last_processed_email_id = email['id']
#
#             # Wait before checking for new emails
#             time.sleep(10)  # Check every 10 seconds
#
#         except Exception as e:
#             print(f"An error occurred in the main loop: {e}")
#             time.sleep(30)  # Wait longer if there's an error
#             continue
#
#
# if __name__ == "__main__":
#     CLIENT_SECRET_FILE = "client_secret.json"  # Update this with your actual credentials file
#     monitor_new_emails(CLIENT_SECRET_FILE)

import os
import time
import base64
import google.generativeai as genai
from google_apis import create_service
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from collections import deque
from time import sleep
from calender import EventExtractor  # Import the EventExtractor class
from transformers import pipeline  # For intent classification

from realtime.notion import extract_task_details, add_entry_to_notion

NOTION_API_KEY = "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"
DATABASE_ID = "194588bb4218810cbfd6d66355b3a909"
NOTION_ENDPOINT = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window  # in seconds
        self.requests = deque()

    def can_make_request(self):
        now = datetime.now()
        # Remove old requests
        while self.requests and (now - self.requests[0]) > timedelta(seconds=self.time_window):
            self.requests.popleft()

        # Check if we can make a new request
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

    def wait_for_available_slot(self):
        while not self.can_make_request():
            sleep(1)  # Wait for 1 second before checking again


def init_gmail_service(client_file, api_name='gmail', api_version='v1',
                       scopes=['https://www.googleapis.com/auth/gmail.modify',
                               'https://www.googleapis.com/auth/gmail.send',
                               'https://www.googleapis.com/auth/gmail.readonly']):
    return create_service(client_file, api_name, api_version, scopes)


def _extract_body(payload):
    body = '<Text body not available>'
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    elif 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    return body


def get_latest_email(service, user_id='me'):
    try:
        result = service.users().messages().list(userId=user_id, maxResults=1, q="in:inbox category:primary").execute()
        messages = result.get('messages', [])

        if not messages:
            return None

        msg = messages[0]
        msg_id = msg['id']
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
        payload = message['payload']
        headers = payload.get('headers', [])

        subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
        sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'No sender')
        date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'No date')
        body = _extract_body(payload)

        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body
        }
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def generate_email_response(email_body, rate_limiter):
    try:
        # Wait for an available slot in the rate limiter
        rate_limiter.wait_for_available_slot()

        genai.configure(api_key='AIzaSyDZdkCDQ9ugDLqmFkK0vzWZJUQdEi9cEaQ')
        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
        Generate a professional email response based on this email content:
        {email_body}

        The response should:
        1. Acknowledge the main points of the original email
        2. Be professional and courteous
        3. Provide relevant information or next steps
        4. Keep the tone friendly but professional
        """

        response = model.generate_content(prompt)
        return response.text if response else "I apologize, but I am unable to generate a response at this moment. Please try again later."
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I apologize, but I am unable to generate a response at this moment. Please try again later."


def send_email(service, to, subject, body):
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        return sent_message
    except Exception as e:
        print(f"Error sending email: {e}")
        return None


def generate_email_summary(email_body):
    genai.configure(api_key='AIzaSyDZdkCDQ9ugDLqmFkK0vzWZJUQdEi9cEaQ')
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(f"Summarize this email: {email_body}")
    return response.text if response else "Summary not available."


def check_meeting_intent(email_body):
    """
    Check if the email intends to schedule a meeting using keyword matching.
    """
    # Define a list of keywords and phrases commonly used to schedule meetings
    meeting_keywords = [
        "schedule", "meeting", "meet", "appointment", "discuss",
        "call", "talk", "chat", "conference", "arrange",
        "organize", "plan", "coordinate", "fix", "book",
        "request", "propose", "set up", "follow up", "check-in"
    ]

    # Convert the email body to lowercase for case-insensitive matching
    email_body_lower = email_body.lower()

    # Check if any of the meeting-related keywords are present in the email body
    for keyword in meeting_keywords:
        if keyword in email_body_lower:
            return True

    return False


def monitor_new_emails(client_file):
    service = init_gmail_service(client_file)
    if not service:
        print("Failed to initialize Gmail service.")
        return

    # Initialize rate limiter (60 requests per minute)
    rate_limiter = RateLimiter(max_requests=60, time_window=60)

    # Initialize EventExtractor for calendar functionality
    event_extractor = EventExtractor()

    last_processed_email_id = None

    while True:
        try:
            print("Checking for new emails...")
            email = get_latest_email(service)

            if email and email['id'] != last_processed_email_id:
                print("\nNew Email Found:")
                print(f"From: {email['sender']}")
                print(f"Subject: {email['subject']}")
                print(f"Body: {email['body']}")
                print(f"Date: {email['date']}")

                # Generate email summary
                summary = generate_email_summary(email['body'])
                print(f"Summary: {summary}")

                # Check if the email intends to schedule a meeting
                if check_meeting_intent(email['body']):
                    print("\nEmail intends to schedule a meeting.")
                    # Extract event details from the email body
                    event_details = event_extractor.extract_event_details(email['body'])
                    print("\nExtracted Event Details:")
                    for key, value in event_details.items():
                        print(f"{key}: {value}")

                    # Create a calendar event
                    print("\nCreating calendar event...")
                    event_result = event_extractor.create_calendar_event(event_details)
                    print(event_result)
                else:
                    print("\nEmail does not intend to schedule a meeting.")

                task_data = extract_task_details(email['body'])
                if task_data:
                    print("\nExtracted Task Details:")
                    for key, value in task_data.items():
                        print(f"{key}: {value}")

                    # Step 2: Add task details to Notion
                    print("\nAdding task to Notion...")
                    add_entry_to_notion(task_data)
                # Generate and send email response
                response = generate_email_response(email['body'], rate_limiter)
                if response:
                    print("\nSending response...")
                    send_email(service, email['sender'], email['subject'], response)
                    print("Response sent successfully!")

                last_processed_email_id = email['id']

            # Wait before checking for new emails
            time.sleep(10)  # Check every 10 seconds

        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(30)  # Wait longer if there's an error
            continue


if __name__ == "__main__":
    CLIENT_SECRET_FILE = "client_secret.json"  # Update this with your actual credentials file
    monitor_new_emails(CLIENT_SECRET_FILE)