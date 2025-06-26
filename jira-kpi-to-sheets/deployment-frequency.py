"""
This script calculates deployment frequency KPIs from Jira issues and updates a Google Sheet for reporting.

Main tasks:
- Connects to Jira to fetch issue data related to deployments.
- Calculates deployment frequency metrics over a specified period.
- Updates a Google Sheet ("Production Reliability Workbook" > "Deployment Frequency") with the calculated KPIs.

Environment variables required:
- JIRA_API_TOKEN: Jira API token for authentication.
- JIRA_EMAIL: Jira user email for authentication.
- GOOGLE_APPLICATION_CREDENTIALS (optional): Path to Google service account credentials.

Dependencies:
- requests
- python-dotenv
- gspread
"""

import requests, yaml
import os
from dotenv import load_dotenv
import gspread
import datetime


load_dotenv()

# Initialize Google Sheets client using service account credentials
# This requires a service_account.json file in the project directory
# In GitHub Actions, this file is created from a base64-encoded secret
# gc = gspread.service_account()


# Use the
service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
gc = gspread.service_account(filename=service_account_path)


# Get JIRA credentials from environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Load teams from YAML file
# This file contains a list of the teams 
teams = yaml.safe_load(open('teams.yml'))['teams']

#Instantiate with Credentials
jira = requests.Session()
jira.auth = (JIRA_USERNAME, JIRA_API_TOKEN) 
# Set JIRA API URL
jira_api_url = f"{JIRA_URL}/rest/api/3/search"
# Define JQL query to get issues moved to Done in the last 7 days

# 'project = "HQ" AND status CHANGED TO "DEPLOYED TO PROD" DURING (-7d, now()) OR status CHANGED TO "POST DEPLOYMENT CHECKS" DURING ("2025-01-01 00:00", "2025-01-31 23:59")'

def get_jql_query_for_team(team):
    # jql_query = f'project = "{team}" AND status CHANGED FROM "DEPLOYED TO PROD" DURING ("2025-01-01 00:00", "2025-01-31 23:59")' # For looking for specific date ranges
    if team == 'Cross Border Product Development':
        return f'project = "{team}" AND status CHANGED TO "POST-DEPLOYMENT QA" DURING (-7d, now())'
    elif team == 'HQ':
        return f'project = "HQ" AND status CHANGED TO "DEPLOYED TO PROD" DURING (-7d, now()) OR status CHANGED TO "POST DEPLOYMENT CHECKS" DURING (-7d, now())'
    elif team == 'Kele Mobile App':
        return f'project = "{team}" AND status CHANGED TO "POST DEPLOYMENT TEST" DURING (-7d, now())'
    elif team == 'Stablecoin VS':
        return f'project = "{team}" AND status CHANGED TO "POST DEPLOYMENT QA" DURING (-7d, now())'
    elif team == 'Global Collection':
        return f'project = "{team}" AND status CHANGED TO "POST DEPLOYMENT QA" DURING (-7d, now())'
    else:
        return None

def get_deployments_per_engineer(team,team_size=None, jql_query=None):
    params = {
        'jql': jql_query,
        'fields': 'assignee',
        'startAt': 0,
        'maxResults': 1000
    }

    try:
        response = jira.get(jira_api_url, params=params)
        response.raise_for_status()
        
        issues = response.json().get('issues', [])
        deployments_by_engineer = {}

        for issue in issues:
            assignee = issue.get('fields', {}).get('assignee', {})
            engineer = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            deployments_by_engineer[engineer] = deployments_by_engineer.get(engineer, 0) + 1

        total_deployments = sum(deployments_by_engineer.values())
        if 'Unassigned' in deployments_by_engineer:
            del deployments_by_engineer['Unassigned']

        num_engineers = len(deployments_by_engineer) or 1  # Prevent division by zero
        avg_deployments = total_deployments / num_engineers

        # if team_size:
        #     avg_deployments = total_deployments / team_size if team_size > 0 else 0
        # else:
        #     num_engineers = len(deployments_by_engineer) or 1  # Prevent division by zero
        #     avg_deployments = total_deployments / num_engineers

        return team, deployments_by_engineer, total_deployments, avg_deployments

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from JIRA: {e}")
        return {}
    

def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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


def main():
    rows = []
    weekly_date_range = get_weekly_date_range()
    timestamp_value = timestamp()

    for team in teams:
        jql_query = get_jql_query_for_team(team)
        if not jql_query:
            continue
        # team_size = len(teams[team]) if isinstance(teams[team], list) else None
        team_name, deployments_by_engineer, total_deployments, avg_deployments = get_deployments_per_engineer(team, team_size=None, jql_query=jql_query)

        # Create a row for each engineer
        for engineer, deployment_count in deployments_by_engineer.items():
            # Include total_deployments only for the first engineer
            if engineer == list(deployments_by_engineer.keys())[0]:
                row = [timestamp_value, team_name, total_deployments, engineer, deployment_count, avg_deployments]
            else:
                row = ["", "", "", engineer, deployment_count]
            # row = [current_date, total_deployments, engineer, deployment_count]
            rows.append(row)

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Deployments per Engineer")
    
    # Add the date separator row
    worksheet.append_rows([weekly_date_range], value_input_option="USER_ENTERED")

    # Add the development row
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    print(f"Successfully updated Deployments per Engineer & Deployment Frequency data for the week: {weekly_date_range[0]}")
#     print(f"Successfully updated Deployments per Engineer & Deployment Frequency data for the week: {weekly_date_range[0]}")

if __name__ == "__main__":
    main()

# if __name__ == "__main__":

#     for team in teams:
#         jql_query = get_jql_query_for_team(team)
#         get_deployments_per_engineer(team_size=None, jql_query=jql_query)
    
#     rows = []
#     team, deployments_by_engineer, total_deployments, avg_deployments = get_deployments_per_engineer()
#     timestamp_value = timestamp()
#     weekly_date_range = get_weekly_date_range()


#     # Create a row for each engineer
#     for engineer, deployment_count in deployments_by_engineer.items():
#         # Include total_deployments only for the first engineer
#         if engineer == list(deployments_by_engineer.keys())[0]:
#             row = [timestamp_value, total_deployments, engineer, deployment_count, avg_deployments]
#         else:
#             row = [timestamp_value, "", engineer, deployment_count]
#         # row = [current_date, total_deployments, engineer, deployment_count]
#         rows.append(row)