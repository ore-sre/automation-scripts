import os, requests, time
from dotenv import load_dotenv
import gspread
import datetime

# Load environment variables from .env file (for local development)
# In GitHub Actions, these will be provided as environment variables
load_dotenv()

# Initialize Google Sheets client using service account credentials
# This requires a service_account.json file in the project directory
# In GitHub Actions, this file is created from a base64-encoded secret
gc = gspread.service_account()


# Use the path from environment variable or default to service_account.json in current directory
# service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
# gc = gspread.service_account(filename=service_account_path)

# Get New Relic credentials from environment variables
# These are set in .env file locally or in GitHub Secrets for Actions
NR_API_KEY = os.getenv("NEW_RELIC_API_KEY")
ACCOUNT_ID = int(os.getenv("ACCOUNT_ID"))

# New Relic GraphQL API endpoint (EU region)
# Change to https://api.newrelic.com/graphql for US region
url = f"https://api.eu.newrelic.com/graphql"

# Set up request headers with authentication
headers = {
    "X-Api-Key": NR_API_KEY,
    "Content-Type": "application/json",  # Required for GraphQL requests
}

def get_transaction_success_rate():
    # Define NRQL query to get transaction success rate
    nrql = (
        "SELECT "
        "("
        "  ("
        "    filter(count(*),"
        "      WHERE message LIKE '%event.payment.completed%'"
        "        AND aparse(message, '%\"status\":\"*\"%' ) = 'success'"
        "    )"
        "    * 100.0"
        "    /"
        "    IF("
        "      filter(count(*), WHERE message LIKE '%event.payment.initiated%') > 0,"
        "      filter(count(*), WHERE message LIKE '%event.payment.initiated%'),"
        "      NULL"
        "    )"
        "  )"
        "  +"
        "  ("
        "    filter(count(*),"
        "      WHERE name = 'payout.completed'"
        "        AND data.status = 'successful'"
        "    )"
        "    * 100.0"
        "    /"
        "    IF("
        "      filter(count(*), WHERE name = 'payout.initiated') > 0,"
        "      filter(count(*), WHERE name = 'payout.initiated'),"
        "      NULL"
        "    )"
        "  )"
        "  +"
        "  ("
        "    filter(count(*),"
        "      WHERE event = 'event.collection.completed'"
        "    )"
        "    * 100.0"
        "    /"
        "    IF("
        "      filter(count(*), WHERE event = 'event.collection.initiated') > 0,"
        "      filter(count(*), WHERE event = 'event.collection.initiated'),"
        "      NULL"
        "    )"
        "  )"
        ")"
        " / 3 AS 'Average Success Rate (%)' "
        "FROM Log "
        "SINCE 1 month ago "
        "UNTIL now "
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

    # Make the API request to New Relic with retries
    max_retries = 3
    retry_delay = 2  # Initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Check if response contains timeout error
            if 'errors' in data and any(err.get('errorClass') == 'TIMEOUT' for err in data.get('errors', [])):
                raise requests.exceptions.RequestException("New Relic API Timeout")
                
            results = data["data"]["actor"]["account"]["nrql"]["results"][0].get("Average Success Rate (%)")

        except (requests.exceptions.RequestException, KeyError) as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
            print(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    return results

get_transaction_success_rate()

# Function to get current timestamp

def get_month():
    last_month = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)
    return last_month.strftime("%B %Y")

# Main execution block
if __name__ == "__main__":

    month = get_month()

    rows = []
    transaction_success_rate = get_transaction_success_rate()

        # Create a row with all metrics for this service
    rows.append([
        month,
        transaction_success_rate
        ])

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Transaction Success rate")

    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    
    print(f"Successfully updated transaction rate.")