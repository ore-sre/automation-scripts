import requests
import os
import json
from dotenv import load_dotenv
import gspread

load_dotenv()

gc = gspread.service_account()

NR_API_KEY = os.getenv("NEW_RELIC_API_KEY")
APP_ID = os.getenv("APP_ID")

url = f"https://api.eu.newrelic.com/v2/applications/{APP_ID}/metrics.json"

headers = {
    "X-Api-Key": NR_API_KEY,
    "Content-Type": "application/json",
}

response = requests.get(url, headers=headers)

print("Status Code:", response.status_code)

# if response.status_code == 200:
#     data = response.json()
#     print("Data:", data)
# else:
#     print("Failed to fetch data")

sh = gc.open("Production Reliability Workbook")
worksheet = sh.worksheet("Incident Tracker")

print(worksheet.get('d2'))

worksheet_list = sh.worksheets()
print(worksheet_list)
