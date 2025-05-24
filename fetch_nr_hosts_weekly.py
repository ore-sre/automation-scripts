import os, requests, yaml, json
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

# Load hosts from YAML file
# This file contains a list of New Relic host GUIDs to monitor
hosts = yaml.safe_load(open('host_guids.yml'))['hosts']

# New Relic GraphQL API endpoint (EU region)
# Change to https://api.newrelic.com/graphql for US region
url = f"https://api.eu.newrelic.com/graphql"

# Set up request headers with authentication
headers = {
    "X-Api-Key": NR_API_KEY,
    "Content-Type": "application/json",  # Required for GraphQL requests
}

# Function to fetch average CPU usage for a host
def fetch_avg_cpu_usage(host_guid):
    # Define NRQL query to get average CPU usage
    nrql = (
            f"FROM SystemSample "
            f"SELECT average(cpuPercent) AS average_cpu_usage "
            f"WHERE entityGuid = '{host_guid}' "
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
    avg_cpu_usage = results[0]["average_cpu_usage"]
    return avg_cpu_usage
    

# Function to fetch average memory usage for a host
def fetch_avg_memory_usage(host_guid):
    # Define NRQL query to get average memory usage
    nrql = (
            f"FROM SystemSample "
            f"SELECT average(memoryUsedPercent) AS average_memory_usage "
            f"WHERE entityGuid = '{host_guid}' "
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
    avg_memory_usage = results[0]["average_memory_usage"]
    return avg_memory_usage

# Function to fetch average disk usage for a host
def fetch_avg_disk_usage(host_guid):
    # Define NRQL query to get average disk usage
    nrql = (
            f"FROM SystemSample "
            f"SELECT average(diskUsedPercent) AS average_disk_usage "
            f"WHERE entityGuid = '{host_guid}' "
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
    avg_disk_usage = results[0]["average_disk_usage"]
    return avg_disk_usage

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

# Convert Host GUID to Host Name
def convert_host_guid_to_name(host_guid):
    if host_guid == "NDMwMTE1NHxJTkZSQXxOQXw2ODM4MzU1NDMxNDk4MDcyNTYw":
        return "fincra-gateway-prod"
    elif host_guid == "NDMwMTE1NHxJTkZSQXxOQXw4NTI5MDE4OTE2MjI0OTA5MjMw":
        return "fincra-notifications-prod"
    elif host_guid == "NDMwMTE1NHxJTkZSQXxOQXwtMzUyMzYwOTI4NDMyNDg3NTI2NA":
        return "checkout-app-prod"
    elif host_guid == "NDMwMTE1NHxJTkZSQXxOQXwxODI2OTMyNTk5MDAwOTgyNjQ2":
        return "checkout-core-prod"

# Main execution block
if __name__ == "__main__":
    rows = []
    for host_guid in hosts:
        print(f"Fetching metrics for {host_guid}...")
        avg_cpu_usage = fetch_avg_cpu_usage(host_guid)
        avg_memory_usage = fetch_avg_memory_usage(host_guid)
        avg_disk_usage = fetch_avg_disk_usage(host_guid)
        timestamp = get_current_timestamp()
        date_row = get_weekly_date_range()
        host_name = convert_host_guid_to_name(host_guid) 
        
        # Create a row with all metrics for this host
        rows.append([
            timestamp,
            host_name,
            avg_cpu_usage,
            avg_memory_usage,
            avg_disk_usage,
        ])
    
    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Weekly HOSTS Metrics")
    
    # Add the date separator row
    worksheet.append_rows([date_row], value_input_option="USER_ENTERED")
    
    # Add the metrics rows
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    
    print(f"Successfully updated metrics for {len(hosts)} hosts.")