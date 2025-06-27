"""
This script monitors the health and status of infrastructure automation workflows in Fincra's infrastructure repositories.

Main tasks:
- Loads a list of infrastructure repositories from a YAML configuration file.
- Fetches the latest workflow run status from GitHub Actions for each repository.
- Aggregates and reports the health status of automation workflows.
- Updates a Google Sheet ("Production Reliability Workbook" > "Infra Automation Health Check") with the health check results.

Environment variables required:
- FINCRA_GITHUB_TOKEN: GitHub token for API authentication.
- GOOGLE_APPLICATION_CREDENTIALS (optional): Path to Google service account credentials.

Dependencies:
- requests
- PyYAML
- python-dotenv
- gspread
"""

import requests, yaml
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import gspread

load_dotenv()

# Initialize Google Sheets client using service account credentials
# This requires a service_account.json file in the project directory
# In GitHub Actions, this file is created from a base64-encoded secret
# gc = gspread.service_account()


# Use the path from environment variable or default to service_account.json in current directory
service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
gc = gspread.service_account(filename=service_account_path)

# Load Infrastructure repos from yaml file
infrastructure_repos = yaml.safe_load(open('infrastructure-repos.yml'))['infrastructure-repos']


org_name = "FincraNG"
repo_name = "fincra-disbursements"
token = os.getenv("FINCRA_GITHUB_TOKEN")

# def get_org_repos():
#     """
#     Fetch all repositories for a GitHub organization.
    
#     Args:
#         org_name (str): Name of the GitHub organization
#         token (str): GitHub personal access token
    
#     Returns:
#         List[dict]: List of repository information
#     """
#     base_url = f"https://api.github.com/orgs/{org_name}/repos"
#     headers = {
#         "Authorization": f"token {token}",
#         "Accept": "application/vnd.github.v3+json"
#     }
    
#     repos_info = []
#     repos = []
#     page = 1
    
#     while True:
#         response = requests.get(
#             f"{base_url}?page={page}&per_page=100",
#             headers=headers
#         )
        
#         if response.status_code != 200:
#             raise Exception(f"Failed to fetch repos: {response.status_code}")
            
#         page_repos = response.json()
#         if not page_repos:
#             break
            
#         repos_info.extend(page_repos)
#         page += 1  

#     print(f"Found {len(repos_info)} repositories:")
#     for repo in repos_info:
#         repos.append(repo['name'])
     
#     return repos


def get_workflow_stats():
    """Get statistics for workflow runs across all repos"""
    repos = infrastructure_repos
    
    total_runs = 0
    successful_runs = 0
    failed_runs = 0
    failed_actions = []

    for repo_name in repos:
        base_url = f"https://api.github.com/repos/{org_name}/{repo_name}/actions/runs"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        yesterday = datetime.now() - timedelta(days=1)
        
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            continue   
        runs = response.json()["workflow_runs"]
        recent_runs = [
            run for run in runs 
            if datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ") > yesterday
        ]

        total_runs += len(recent_runs)

        for run in recent_runs:
            if run["conclusion"] == "success":
                successful_runs += 1
            elif run["conclusion"] == "failure":
                failed_runs += 1
                failed_actions.append({
                    "repo": repo_name,
                    "name": run["name"],
                    "url": run["html_url"]
                })
        
        
    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "failed_actions": failed_actions
    }

def update_google_sheet(stats):
    """Update Google Sheet with workflow statistics"""
    rows = [[
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        stats["total_runs"],
        stats["successful_runs"],
        stats["failed_runs"],
    ]]
    
    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Infra Automation Health Check")
    
    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    
    print(f"Successfully updated sheet with {len(rows)} entries.")

def main():
    stats = get_workflow_stats()
    print(f"Total runs: {stats['total_runs']}")
    print(f"Successful runs: {stats['successful_runs']}")
    print(f"Failed runs: {stats['failed_runs']}")
    
    if stats["failed_actions"]:
        print("\nFailed actions:")
        for action in stats["failed_actions"]:
            print(f"- {action['repo']}: {action['name']} ({action['url']})")
    update_google_sheet(stats)

if __name__ == "__main__":
    main()
