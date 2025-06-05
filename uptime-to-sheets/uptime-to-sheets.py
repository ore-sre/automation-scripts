import requests
import gspread
import os   
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# In GitHub Actions, these will be provided as environment variables
load_dotenv()

# Initialize Google Sheets client using service account credentials
# This requires a service_account.json file in the project directory
# In GitHub Actions, this file is created from a base64-encoded secret
# gc = gspread.service_account()


# Use the path from environment variable or default to service_account.json in current directory
service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
gc = gspread.service_account(filename=service_account_path)




url = "https://api.uptimerobot.com/v2/getMonitors"

def get_uptime_data():
   
    payload = {
        'api_key': os.getenv('UPTIME_ROBOT_API_KEY'),
        'format': 'json',
        "custom_uptime_ratios": "1",
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()  # Raise exception for HTTP errors
    
    # Parse the response JSON
    data = response.json()
    return data

# Function to get current timestamp
def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_overall_uptime():
    data = get_uptime_data()
    if 'monitors' not in data:
        raise Exception(f"UptimeRobot API error or invalid response: {data}")
    total_uptime = 0.0
    total_up_checks = 0
    total_checks = 0
    
    for monitor in data['monitors']:
        status = monitor.get("status")
        if status == 0:
        # Skip paused monitors
            continue

        # Proceed with uptime calculations for active monitors
        interval_secs = monitor.get("interval")
        if not interval_secs:
            continue  # Skip monitors without an interval

        uptime_24h = float(monitor['custom_uptime_ratio'])
        total_uptime += uptime_24h

        interval = monitor.get('interval', None) 
    
        # 86,400 seconds in a day ÷ interval_in_seconds
        checks_per_24h = 86400.0 / interval

        # Calculate up and total checks
        up_checks = (uptime_24h / 100) * checks_per_24h
        total_up_checks += up_checks
        total_checks += checks_per_24h

    # Calculate the overall uptime percentage
    overall_pct_uptime = (total_up_checks / total_checks) * 100

    return overall_pct_uptime
    
# Main execution block
if __name__ == "__main__":
    row = [timestamp(), get_overall_uptime()]
    
    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Daily Uptime Dashboard")
    
    # Add the uptime row
    worksheet.append_rows([row], value_input_option="USER_ENTERED")

    print(f"Successfully updated uptime")
