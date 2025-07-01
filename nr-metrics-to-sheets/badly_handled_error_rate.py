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



def fetch_badly_handled_error_rate():
    # Define NRQL query to get error count
    nrql = (
        f"SELECT "
        f"filter(count(*), WHERE level = 'error') as totalErrors, "
        f"filter(count(*), WHERE level = 'error' AND (error.httpCode IS NULL OR eerror.httpCode = '')) as badlyHandledErrors, "
        f"(filter(count(*), WHERE level = 'error' AND (error.httpCode IS NULL OR error.httpCode = '')) * 100.0 / filter(count(*), WHERE level = 'error')) as badlyHandledRate "
        f"FROM Log "
        f"SINCE 30 days ago "
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
    return results
    


def get_month():
    last_month = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)
    return last_month.strftime("%B %Y")

# Main execution block
if __name__ == "__main__":
    rows = []
    total_errors = fetch_badly_handled_error_rate()[0]['totalErrors']
    badly_handled_errors = fetch_badly_handled_error_rate()[0]['badlyHandledErrors']
    badly_handled_error_rate = fetch_badly_handled_error_rate()[0]['badlyHandledRate'] 
    month = get_month()
    
    rows.append([
                month,
                total_errors,
                badly_handled_errors,
                badly_handled_error_rate,
            ])

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Badly Handled ErrorRate")
        
    # Add the logs rows
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    print(f"Successfully updated Badly Handled Error Rate data for the month: {month}")

