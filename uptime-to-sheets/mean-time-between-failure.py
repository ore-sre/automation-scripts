import requests, yaml
import gspread
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
"""
    This script calculates the Mean Time Between Failures (MTBF) for uptime monitoring
    and updates a Google Sheet with the results.

"""


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


# Load Infrastructure repos from yaml file
internal_services = yaml.safe_load(open('monitors.yml'))['internal-services']


url = "https://api.uptimerobot.com/v2/getMonitors"

# UNIX timestamp for the last 30 days
now = datetime.now(timezone.utc)
# For the year
# start_of_year = datetime(now.year, 1, 1, tzinfo=timezone.utc)
# For the month
start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
# For the past 7 days
# seven_days_ago = now - timedelta(days=7)
# For the day
# start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
# Custom range 
# start_time = datetime(2025, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
# end_time = datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def get_logs_data():

    payload = {
        'api_key': os.getenv('UPTIME_ROBOT_API_KEY'),
        'format': 'json',
        'logs': 1,
        'logs_type': 1,  # 1 for all logs
        'logs_limit': 1000,  # Limit to 1000 logs 
        'show_tags': 1, 
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()  # Raise exception for HTTP errors
    
    # Parse the response JSON
    data = response.json()
    return data



def get_mean_time_between_failures():
    data = get_logs_data()
    # print(data['monitors'][0])
    if 'monitors' not in data:
        raise Exception(f"UptimeRobot API error or invalid response: {data}")
    down_times = []
    
    
    for monitor in data['monitors']:
        #Skip external services
        if monitor['friendly_name'] not in internal_services:
            continue
        status = monitor.get("status")
        if status == 0:
        # Skip paused monitors
            continue
        for log in monitor.get('logs', []):
            log_time = datetime.fromtimestamp(log['datetime'], tz=timezone.utc)

            # if log['type'] == 1 and start_time <= log_time < end_time and log['duration'] > 120:  #Custom range
            if log['type'] == 1 and log['duration'] > 120 and log_time >= start_of_month:  # For the month
                # Type 1 indicates a downtime log
                # print(log)
                down_times.append(log_time)
        # 3. Sort them
        down_times.sort()
    num_failures = len(down_times)
    print(f"Number of failures: {num_failures}")
    intervals = []

    # Calculate intervals between downtimes
    for i in range(1, len(down_times)):
        interval = (down_times[i] - down_times[i - 1]).total_seconds()/3600  # Convert to hours
        if interval > 0:  # Only consider positive intervals
            intervals.append(interval)

    # 5. Calculate MTBF
    if intervals:
        mtbf = sum(intervals) / len(intervals)
    else:
        mtbf = 0

    return num_failures, mtbf

def get_month():
    last_month = datetime.now().replace(day=1) - datetime.timedelta(days=1)
    formatted_month = last_month.strftime("%B %Y")
    return formatted_month

# Main execution block
if __name__ == "__main__":
    
    month = get_month()
    num_failures, mtbf = get_mean_time_between_failures()
    row = [month, num_failures, mtbf]

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Mean Time Between Failures")
    
    # Add the uptime row
    worksheet.append_rows([row], value_input_option="USER_ENTERED")

    print(f"Successfully updated Mean Time Between Failures (MTBF) data for the month: {month}")
