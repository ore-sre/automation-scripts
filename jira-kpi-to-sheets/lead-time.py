import requests, yaml
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

# Load teams from YAML file
# This file contains a list of the teams 
teams = yaml.safe_load(open('teams.yml'))['teams']

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

def get_jql_query_for_team(team):
 # jql_query = 'project = "{team}" AND status CHANGED TO "READY TO DEPLOY" AND status CHANGED FROM "READY TO DEPLOY" DURING ("2025-04-01","2025-04-31")'
    if team == 'Cross Border Product Development':
        return f'project = "{team}" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING (-30d, now())'
    elif team == 'HQ':
        return f'project = "{team}" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING (-30d, now())'
    elif team == 'Kele Mobile App':
        return f'project = "{team}" AND status CHANGED TO "READY TO DEPLOY" AND status CHANGED FROM "READY TO DEPLOY" DURING (-30d, now())'
    elif team == 'Stablecoin VS':
        return f'project = "{team}" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING (-30d, now())'
    elif team == 'Global Collection':
        return f'project = "{team}" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING (-30d, now())'
    else:
        return None
    


#  jql_query = 'project = "Cross Border Product Development" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING (-30d, now())'
    # jql_query = 'project = "Cross Border Product Development" AND status CHANGED TO "READY FOR DEPLOYMENT" AND status CHANGED FROM "READY FOR DEPLOYMENT" DURING ("2025-04-01","2025-04-31")'
     
 
def calculate_deployment_to_resolution_lead_time(team, jql_query=None):
   
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
            return team, total_issues, avg_lead_time

    # Get today's date for the date label row
def get_month():
    formatted_month = datetime.datetime.now().strftime("%B %Y")
    # Return the formatted date row
    return [f"▶ {formatted_month} ◀"] + [""] * 6

def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    month = get_month()
    timestamp = timestamp()
    rows = []
    for team in teams:
        jql_query = get_jql_query_for_team(team)
        if not jql_query:
            continue
        
        result = calculate_deployment_to_resolution_lead_time(team, jql_query=jql_query)
        if result:
            team, total_issues, avg_lead_time = result
            row = [timestamp, team, avg_lead_time]
        else:
            row = [timestamp, team, 'N/A']
        # Append the row to the list of rows
        rows.append(row)
    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Lead Time")

     # Add the date separator row
    worksheet.append_rows([month], value_input_option="USER_ENTERED")
   
    # Add the uptime row
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    print(f"Successfully updated lead time data for the month: {month}")

