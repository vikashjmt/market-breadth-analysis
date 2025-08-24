import requests
import os
import sys

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

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
file_mode = None
if len(sys.argv) > 2:
    file_mode = True
if not file_mode:
    file_data = None
    with open(data_file) as fd:
        file_data = fd.readlines()

    file_data_str = ''.join(file_data)
    # response = send_file_to_telegram(data_file, caption="🚨 Market Breadth Analysis Report")
    response = send_telegram_message(file_data_str)
    print(response)
else:
    response = send_file_to_telegram(data_file, caption="🚨 Market MACD Analysis Report")
