# """
# This script calculates the number of story points closed in Jira and updates a Google Sheet for reporting.

# Main tasks:
# - Connects to Jira to fetch issue data and story points.
# - Calculates the total story points closed over a specified period.
# - Updates a Google Sheet ("Production Reliability Workbook" > "Story Points Closed") with the calculated KPIs.

# Environment variables required:
# - JIRA_API_TOKEN: Jira API token for authentication.
# - JIRA_EMAIL: Jira user email for authentication.
# - GOOGLE_APPLICATION_CREDENTIALS (optional): Path to Google service account credentials.

# Dependencies:
# - requests
# - python-dotenv
# - gspread
# - oauth2client
# """

# import os
# import requests
# from dotenv import load_dotenv
# import gspread

# from datetime import datetime, timedelta

# # Load environment variables from .env file
# load_dotenv()

# # Jira API credentials
# JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
# JIRA_EMAIL = os.getenv("JIRA_EMAIL")

# # Google Sheets credentials
# GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
# GOOGLE_SHEET_RANGE = os.getenv("GOOGLE_SHEET_RANGE")

# # Jira API endpoint for searching issues
# JIRA_SEARCH_URL = "https://your-domain.atlassian.net/rest/api/2/search"

# # Google Sheets scope for accessing and editing spreadsheets
# SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# def get_jira_issues(jql_query, start_date, end_date):
#     """
#     Fetches Jira issues based on the JQL query and date range.

#     Args:
#     - jql_query (str): The JQL query to filter issues.
#     - start_date (str): The start date for the query in 'YYYY-MM-DD' format.
#     - end_date (str): The end date for the query in 'YYYY-MM-DD' format.

#     Returns:
#     - list: A list of Jira issues matching the query.
#     """
#     headers = {
#         "Authorization": f"Basic {JIRA_EMAIL}:{JIRA_API_TOKEN}",
#         "Content-Type": "application/json",
#     }

#     jql = f"{jql_query} AND resolved >= '{start_date}' AND resolved <= '{end_date}'"
#     params = {
#         "jql": jql,
#         "fields": "customfield_10004",  # Adjust the field ID based on your Jira configuration
#         "maxResults": 1000,
#     }

#     response = requests.get(JIRA_SEARCH_URL, headers=headers, params=params)
#     response.raise_for_status()

#     data = response.json()
#     return data["issues"]

# def calculate_story_points(issues):
#     """
#     Calculates the total story points from the list of Jira issues.

#     Args:
#     - issues (list): A list of Jira issues.

#     Returns:
#     - int: The total number of story points.
#     """
#     total_story_points = 0
#     for issue in issues:
#         story_points = issue["fields"].get("customfield_10004")  # Adjust the field ID based on your Jira configuration
#         if story_points:
#             total_story_points += story_points
#     return total_story_points

# def update_google_sheet(total_story_points):
#     """
#     Updates the Google Sheet with the total story points closed.

#     Args:
#     - total_story_points (int): The total number of story points closed.
#     """
#     credentials = ServiceAccountCredentials.from_json_keyfile_name(
#         os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), SCOPE
#     )
#     client = gspread.authorize(credentials)

#     sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Story Points Closed")
#     sheet.append_row([str(datetime.now().date()), total_story_points])

# def main():
#     """
#     Main function to execute the KPI calculation and update process.
#     """
#     # Define your JQL query here
#     jql_query = "project = YOUR_PROJECT_KEY AND status = Closed"

#     # Calculate the date range for the last 30 days
#     end_date = datetime.now()
#     start_date = end_date - timedelta(days=30)

#     # Format the dates as strings
#     start_date_str = start_date.strftime("%Y-%m-%d")
#     end_date_str = end_date.strftime("%Y-%m-%d")

#     # Fetch Jira issues
#     issues = get_jira_issues(jql_query, start_date_str, end_date_str)

#     # Calculate total story points
#     total_story_points = calculate_story_points(issues)

#     # Update Google Sheet
#     update_google_sheet(total_story_points)

# if __name__ == "__main__":
#     main()