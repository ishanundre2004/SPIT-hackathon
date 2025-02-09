import requests
import json
import re
from datetime import datetime, timedelta
import google.generativeai as genai
import dotenv
# 🔹 Set up Google Gemini API
GENAI_API_KEY = ""
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# 🔹 Set up Notion API
NOTION_API_KEY = "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"
DATABASE_ID = "194588bb4218810cbfd6d66355b3a909"
NOTION_ENDPOINT = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# # 🔹 Convert "DD/MM/YYYY" to "YYYY-MM-DD" for Notion
# def convert_deadline_to_iso(deadline):
#     try:
#         formatted_date = datetime.strptime(deadline, "%d/%m/%Y").strftime("%Y-%m-%d")
#         return formatted_date
#     except ValueError:
#         print(f"❌ Invalid date format: {deadline}")
#         return None
#
# # 🔹 Extract task details using Gemini
# def extract_task_details(sentence):
#     prompt = f"""
#     Extract the following details from the sentence:
#     - Task: Identify the main task (e.g., "Meeting with OpenAI").
#     - Deadline: Extract and format as DD/MM/YYYY.
#     - Time: Extract and format as HH:MM (24-hour format).
#     - Link: Extract a URL if available; otherwise, return an empty string.
#
#     Sentence: "{sentence}"
#     Output JSON only with keys: Task, Deadline, Time, Link.
#     """
#
#     response = model.generate_content(prompt)
#     print(f"🔍 Raw Response from Gemini: {response.text}")  # Debugging
#
#     json_text = re.sub(r"```json\s+([\s\S]+?)\s+```", r"\1", response.text.strip())
#
#     try:
#         extracted_data = json.loads(json_text)
#         return extracted_data
#     except json.JSONDecodeError as e:
#         print(f"❌ Error parsing response: {e}")
#         return None
#
# # 🔹 Add extracted details to Notion
# def add_entry_to_notion(data):
#     if not data:
#         print("❌ No valid data extracted.")
#         return
#
#     data["Deadline"] = convert_deadline_to_iso(data["Deadline"])
#     if not data["Deadline"]:
#         return  # Skip if date conversion fails
#
#     # Ensure Link is not None
#     data["Link"] = data.get("Link", "")
#
#     # Prepare payload for Notion
#     payload = {
#         "parent": {"type": "database_id", "database_id": DATABASE_ID},
#         "properties": {
#             "Tasks": {"title": [{"type": "text", "text": {"content": data["Task"]}}]},
#             "Deadline": {"date": {"start": data["Deadline"]}},
#             "Time": {"rich_text": [{"type": "text", "text": {"content": data["Time"]}}]},
#             "Link": {"url": data["Link"]} if data["Link"] else {"rich_text": [{"type": "text", "text": {"content": ""}}]},
#         },
#     }
#
#     url = f"{NOTION_ENDPOINT}/pages"
#     response = requests.post(url, headers=HEADERS, json=payload)
#
#     if response.status_code == 200:
#         print(f"✅ Added entry successfully: {data['Task']}")
#     else:
#         print(f"❌ Failed to add entry: {response.text}")

def convert_deadline_to_iso(deadline):
    """
    Convert the deadline to a string format suitable for Notion (as a text field).
    If the deadline is already in a valid format, return it as is.
    If the deadline is None or invalid, return a default value (e.g., "No deadline").
    """
    try:
        if deadline:  # Check if deadline is not None or empty
            # Validate the date format (optional, if you want to ensure it's in DD/MM/YYYY)
            return deadline  # Return the deadline as is (no conversion needed)
        return "No deadline"  # Return a default value if deadline is None or empty
    except ValueError:
        print(f"❌ Invalid date format: {deadline}")
        return "Invalid deadline"  # Return a default value if the format is invalid

# 🔹 Extract task details using Gemini
def extract_task_details(sentence):
    prompt = f"""
    Extract the following details from the sentence:
    - Task: Identify the main task (e.g., "Meeting with OpenAI").
    - Deadline: Extract and format as DD/MM/YYYY.
    - Time: Extract and format as HH:MM (24-hour format).
    - Link: Extract a URL if available; otherwise, return an empty string.

    Sentence: "{sentence}"
    Output JSON only with keys: Task, Deadline, Time, Link.
    """

    response = model.generate_content(prompt)
    print(f"🔍 Raw Response from Gemini: {response.text}")  # Debugging

    json_text = re.sub(r"```json\s+([\s\S]+?)\s+```", r"\1", response.text.strip())

    try:
        extracted_data = json.loads(json_text)
        return extracted_data
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing response: {e}")
        return None

# 🔹 Add extracted details to Notion
def add_entry_to_notion(data):
    if not data:
        print("❌ No valid data extracted.")
        return

    # Ensure all fields are present and handle None values
    task = data.get("Task", "No task specified")
    deadline = convert_deadline_to_iso(data.get("Deadline"))  # Deadline is now a text field
    time = data.get("Time", "No time specified")
    link = data.get("Link", None)

    # Prepare payload for Notion
    payload = {
        "parent": {"type": "database_id", "database_id": DATABASE_ID},
        "properties": {
            "Tasks": {"title": [{"type": "text", "text": {"content": task}}]},
            "Deadline": {"rich_text": [{"type": "text", "text": {"content": deadline}}]},  # Deadline as text
            "Time": {"rich_text": [{"type": "text", "text": {"content": time}}]},
            "Link": {"url": link} if link else {"url": None}
        },
    }

    url = f"{NOTION_ENDPOINT}/pages"
    response = requests.post(url, headers=HEADERS, json=payload)

    if response.status_code == 200:
        print(f"✅ Added entry successfully: {task}")
    else:
        print(f"❌ Failed to add entry: {response.text}")
# 🔹 Main Function
def main():
    input_sentence = "Hello sir, your meeting with Tesla is scheduled on 25/02/2025 at 3 PM. Join via https://meet.openai.com/xyz."
    print(f"📩 Input Sentence: {input_sentence}")

    extracted_data = extract_task_details(input_sentence)
    print(f"🔍 Extracted Data: {extracted_data}")

    add_entry_to_notion(extracted_data)

# Run the script
if __name__ == "__main__":
    main()





