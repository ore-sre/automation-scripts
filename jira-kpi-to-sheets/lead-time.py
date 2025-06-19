import requests
import os
from dotenv import load_dotenv
import gspread
import datetime
from dateutil.parser import parse


load_dotenv()

# Initialize Google Sheets client using service account credentials
# This requires a service_account.json file in the project directory
# In GitHub Actions, this file is created from a base64-encoded secret
# gc = gspread.service_account()


# Use the path from environment variable or default to service_account.json in current directory
service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
gc = gspread.service_account(filename=service_account_path)


# Get JIRA credentials from environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

#Instantiate with Credentials
jira = requests.Session()
jira.auth = (JIRA_USERNAME, JIRA_API_TOKEN) 
# Set JIRA API URL
jira_api_url = f"{JIRA_URL}/rest/api/3/search"
# Define JQL query to get issues moved to Done in the last 7 days

def get_issue_changelog(issue_key):
    start_at = 0
    all_histories = []
    while True:
        changelog_url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/changelog"
        params = {'startAt': start_at, 'maxResults': 100}
        response = jira.get(changelog_url, params=params)
        
        if response.status_code != 200:
            print(f"Failed to fetch changelog for {issue_key}")
            break
            
        data = response.json()
        histories = data.get('values', [])
        all_histories.extend(histories)
        
        if len(histories) < 100:  # No more pages
            break
            
        start_at += 100
    return all_histories

def find_deployment_timestamps(histories):
    entry_time = None
    exit_time = None
    
    for history in histories:
        created = parse(history['created'])
        for item in history.get('items', []):
            if item['field'] == 'status':
                if item['toString'] == 'READY FOR DEPLOYMENT':
                    entry_time = created
                elif item['fromString'] == 'READY FOR DEPLOYMENT':
                    exit_time = created
                    
    return entry_time, exit_time
def calculate_deployment_to_resolution_lead_time():
    jql_query = 'project = "Cross Border Product Development" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING (-30d, now())'
    # jql_query = 'project = "Cross Border Product Development" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING ("2025-04-01","2025-04-31")'
    # Set parameters for the API request
    params = {
        'jql': jql_query,
        'fields': 'created, status, issuetype, resolutiondate, customDocField, summary, reporter',
        'startAt': 0,
        'maxResults': 1000,  # Adjust as needed
    }
    # Make the API request to get issues
    response = jira.get(jira_api_url, params=params)
    if response.status_code == 200:
        issues = response.json().get('issues', [])
        if not issues:
            print("No issues found in the last 7 days.")
            return
            
        total_lead_time = 0
        total_issues = len(issues)

        for issue in issues:
            issue_key = issue['key']
            # Get changelog for each issue
            histories = get_issue_changelog(issue_key)
            # Find deployment timestamps
            entry_time, exit_time = find_deployment_timestamps(histories)
            
            if entry_time and exit_time:
                # Calculate lead time in hours
                lead_time = (exit_time - entry_time).total_seconds() / 3600
                total_lead_time += lead_time
                
        # Calculate average lead time
        if total_issues > 0:
            avg_lead_time = total_lead_time / total_issues
            return total_issues, avg_lead_time

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
    return date_range


if __name__ == "__main__":
    # Get the weekly date range
    date_range = get_weekly_date_range()
    total_issues, avg_lead_time = calculate_deployment_to_resolution_lead_time()
    row = [date_range, total_issues, avg_lead_time]

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Lead Time")
    
    # Add the uptime row
    worksheet.append_rows([row], value_input_option="USER_ENTERED")

    print(f"Successfully updated lead time data for the week: {date_range}")

