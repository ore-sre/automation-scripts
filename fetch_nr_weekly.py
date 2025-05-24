import os, requests, yaml
from dotenv import load_dotenv
import gspread
import datetime

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

# Get New Relic credentials from environment variables
# These are set in .env file locally or in GitHub Secrets for Actions
NR_API_KEY = os.getenv("NEW_RELIC_API_KEY")
ACCOUNT_ID = int(os.getenv("ACCOUNT_ID"))

# Load services from YAML file
# This file contains a list of New Relic application names to monitor
services = yaml.safe_load(open('services.yml'))['services']


# New Relic GraphQL API endpoint (EU region)
# Change to https://api.newrelic.com/graphql for US region
url = f"https://api.eu.newrelic.com/graphql"

# Set up request headers with authentication
headers = {
    "X-Api-Key": NR_API_KEY,
    "Content-Type": "application/json",  # Required for GraphQL requests
}

def fetch_avg_response_time(service_name):
    # Define NRQL query to get average transaction duration in milliseconds
    nrql = (
            f"FROM Metric "
            f"SELECT average(apm.service.transaction.duration) * 1000 AS average_response_time "
            f"WHERE appName = '{service_name}' "
            f"AND transactionType = 'Web' "
            f"SINCE 1 week ago "
            f"UNTIL now"
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
    response.raise_for_status()  # Raise exception for HTTP errors
    
    # Parse the response JSON
    data = response.json()
    results = data["data"]["actor"]["account"]["nrql"]["results"]
    avg_duration = results[0]["average_response_time"]
    return avg_duration

def fetch_error_rate(service_name):
    # Define NRQL query to get error rate
    nrql = (
            f"FROM Metric "
            f"SELECT sum(apm.service.error.count['count']) / count(apm.service.transaction.duration) AS error_rate "
            f"WHERE appName = '{service_name}' "
            f"AND transactionType = 'Web' "
            f"SINCE 1 week ago "
            f"UNTIL now"
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
    error_rate = results[0]["error_rate"]
    return error_rate

def fetch_throughput(service_name):
    # Define NRQL query to get throughput (requests per second)
    nrql = (
            f"FROM Metric "
            f"SELECT rate(count(apm.service.transaction.duration), 1 minute) AS average_throughput "
            f"WHERE appName = '{service_name}' "
            f"AND transactionType = 'Web' "
            f"SINCE 1 week ago "
            f"UNTIL now"
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
    throughput = results[0]["average_throughput"]
    return throughput

# Function to get current timestamp
def timestamp():
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
    # Get current timestamp for data logging
    timestamp = timestamp()
    
    # Get today's date for the date label row
    date_row = get_weekly_date_range()
    
    # Collect metrics for each service
    rows = []
    for svc in services:
        print(f"Fetching metrics for {svc}...")
        avg_rt = fetch_avg_response_time(svc)
        err_rate = fetch_error_rate(svc)
        throughput = fetch_throughput(svc)
        
        # Create a row with all metrics for this service
        rows.append([
            timestamp,
            svc,
            avg_rt,
            err_rate,
            throughput,
        ])
    
    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Weekly APM Metrics")
    
    # Add the date separator row
    worksheet.append_rows([date_row], value_input_option="USER_ENTERED")
    
    # Add the metrics rows
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    
    print(f"Successfully updated metrics for {len(services)} services.")


