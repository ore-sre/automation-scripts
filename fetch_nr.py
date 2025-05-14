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
            f"SINCE 1 day ago "
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
            f"SINCE 1 day ago "
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
            f"SINCE 1 day ago "
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
    
# Main execution block
if __name__ == "__main__":
    # Get current timestamp for data logging
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get today's date for the date label row
    today_label = datetime.datetime.now().date()
    
    # Create a row with the date label (with empty cells for alignment)
    date_row = [f"▶ {today_label} ◀"] + [""] * 4
    
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
    worksheet = sh.worksheet("APM Metrics Report")
    
    # Add the date separator row
    worksheet.append_rows([date_row], value_input_option="USER_ENTERED")
    
    # Add the metrics rows
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    
    print(f"Successfully updated metrics for {len(services)} services.")


