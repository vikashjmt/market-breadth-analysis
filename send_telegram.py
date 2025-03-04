import requests
import os
import sys

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
MAX_LENGTH = 2048

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    return response.json()

def send_file_to_telegram(file_path, caption="🚨 Market Breadth Report 📊"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(file_path, "rb") as file:
        payload = {
            "chat_id": CHAT_ID,
            "caption": caption  # Optional message with file
        }
        files = {
            "document": file
        }
        response = requests.post(url, data=payload, files=files)
    return response.json()

# Example Usage
data_file = sys.argv[1]
response = send_file_to_telegram(data_file, caption="🚨 Market Breadth Analysis Report")
#print(response)
