import os, requests, yaml, json
from dotenv import load_dotenv
import gspread
import datetime

# Load environment variables from .env file (for local development)
# In GitHub Actions, these will be provided as environment variables
load_dotenv()

# gc = gspread.service_account()

# Initialize Google Sheets client using service account credentials
# Use the path from environment variable or default to service_account.json in current directory
service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
gc = gspread.service_account(filename=service_account_path)

# Get New Relic credentials from environment variables
# These are set in .env file locally or in GitHub Secrets for Actions
NR_API_KEY = os.getenv("NEW_RELIC_API_KEY")
ACCOUNT_ID = int(os.getenv("ACCOUNT_ID"))

# Load services from YAML file
# This file contains a list of New Relic application names to monitor
services = yaml.safe_load(open('services.yml'))['services']


# New Relic GraphQL API endpoint (EU region)
url = f"https://api.eu.newrelic.com/graphql"

# Set up request headers with authentication
headers = {
    "X-Api-Key": NR_API_KEY,
    "Content-Type": "application/json",  # Required for GraphQL requests
}

def fetch_error_logs(service_name):
    # Define NRQL query to get error logs
    nrql = (
            f"FROM Log "
            f"SELECT Count(*) AS `count`, max(timestamp) AS `lastSeen` "
            f"WHERE entity.name = '{service_name}' "
            f"AND level = 'error' "
            f"SINCE 1 week ago "
            f"UNTIL now "
            f"FACET message, error.httpCode "
            f"LIMIT 5 "
            )

    # Construct the GraphQL query with variables
    payload = {
            "query": """
            query($accountId: Int!, $nrql: Nrql!) {
                actor {
                account(id: $accountId) {
                    nrql(query: $nrql) {
                    results
                    }
                }
                }
            }
            """,
            "variables": {
                "accountId": ACCOUNT_ID,
                "nrql": nrql
            }
        }
    
    # Make the API request to New Relic
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    #Parse the response JSON      
    data = response.json()
    results = data["data"]["actor"]["account"]["nrql"]["results"]
    return results

# Fetch error logs for checkout-core-prod

# Fetch total count of errors for a service
def fetch_error_count(service_name):
    # Define NRQL query to get error count
    nrql = (
            f"FROM Log "
            f"SELECT Count(*) AS `count` "
            f"WHERE entity.name = '{service_name}' "
            f"AND level = 'error' "
            f"SINCE 1 week ago "
            f"UNTIL now "
            )

    # Construct the GraphQL query with variables
    payload = {
            "query": """
            query($accountId: Int!, $nrql: Nrql!) {
                actor {
                account(id: $accountId) {
                    nrql(query: $nrql) {
                    results
                    }
                }
                }
            }
            """,
            "variables": {
                "accountId": ACCOUNT_ID,
                "nrql": nrql
            }
        }
    
    # Make the API request to New Relic
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    # Parse the response JSON
    data = response.json()
    results = data["data"]["actor"]["account"]["nrql"]["results"]
    error_count = results[0]["count"]
    return error_count

# Convert lastseen to human-redable string
def convert_lastseen(lastseen):
    return datetime.datetime.fromtimestamp(lastseen/1000).strftime("%Y-%m-%d %H:%M:%S")

# Function to get current timestamp
def get_current_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Function to create a date label row like Sunday, May 14th 2025 - Saturday, May 20th 2025
def get_weekly_date_range():
    # Get today's date
    today = datetime.datetime.now().date()
    
    # Calculate the start of the week (previous Sunday)
    start_of_week = today - datetime.timedelta(days=today.weekday() + 1)
    
    # Calculate the end of the week (next Saturday)
    end_of_week = start_of_week + datetime.timedelta(days=6)
    
    # Function to add ordinal suffix to day
    def add_ordinal_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    
    # Format start date as "Sunday, May 14th 2025"
    start_day_with_suffix = add_ordinal_suffix(start_of_week.day)
    start_date_formatted = start_of_week.strftime(f"%A, %B {start_day_with_suffix} %Y")
    
    # Format end date as "Saturday, May 20th 2025"
    end_day_with_suffix = add_ordinal_suffix(end_of_week.day)
    end_date_formatted = end_of_week.strftime(f"%A, %B {end_day_with_suffix} %Y")
    
    # Combine into a range string
    date_range = f"{start_date_formatted} - {end_date_formatted}"
    
    # Return the formatted date row
    return [f"▶ {date_range} ◀"] + [""] * 6

# Main execution block
if __name__ == "__main__":
    rows = []
    for svc in services:
        print(f"Fetching logs for {svc}...")
        error_logs = fetch_error_logs(svc)
        total_errors = fetch_error_count(svc)
        timestamp = get_current_timestamp()
        date_row = get_weekly_date_range()   
                    
        # If no errors found, add a row with a message and continue to next service
        if not error_logs:
            rows.append([timestamp,svc, "No errors found", "N/A", "N/A", "N/A", "N/A"])
            print(f"No errors found for {svc}")
            continue

        for entry in error_logs:
            message, code_str = entry["facet"]
            error_code = "N/A" if code_str is None else int(code_str)
            count = entry["count"]
            last_seen = convert_lastseen(entry["lastSeen"])
            pct_of_total_errors = count / total_errors * 100

            # Create a row with all metrics for this service
            rows.append([
                timestamp,
                svc,
                message,
                error_code,
                count,
                f"{pct_of_total_errors:.2f}%",
                last_seen
            ])

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Weekly Error Logs")
        
    # Add the date separator row
    worksheet.append_rows([date_row], value_input_option="USER_ENTERED")
        
    # Add the logs rows
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        
    print(f"Successfully updated error logs for {len(services)} services.")

