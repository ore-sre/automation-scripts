"""
This script is a KPI tool for monitoring the stability and success rate of infrastructure automation pipelines, specifically the "apply" workflows in Fincra's infrastructure repositories.

It performs the following tasks:
- Loads a list of infrastructure repositories from a YAML configuration file.
- Fetches workflow run statistics from GitHub Actions for each repository in the last 30 days, focusing on "apply" workflows.
- Calculates the total number of runs, successful runs, failed runs, and collects details of failed actions.
- Updates a Google Sheet ("Production Reliability Workbook" > "Infra Automation Health Check") with the aggregated statistics for monitoring and reporting purposes.

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


def get_terraform_apply_workflow_stats():
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

        # For specific date range
        # start_date = datetime(2025, 6, 1)
        # end_date = datetime(2025, 7, 1)

        # response = requests.get(base_url, headers=headers)
        # if response.status_code != 200:
        #     continue   
        # runs = response.json()["workflow_runs"]
        # apply_monthly_runs = [
        #     run for run in runs
        #     if start_date <= datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ") < end_date and "apply" in run["path"]
        # ]

        one_month_ago = datetime.now() - timedelta(days=30)

        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            continue   
        runs = response.json()["workflow_runs"]
        apply_monthly_runs = [
            run for run in runs
            if datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ") > one_month_ago and "apply" in run["path"]
        ]

        total_runs += len(apply_monthly_runs)

        for run in apply_monthly_runs:
            if run["conclusion"] == "success":
                successful_runs += 1
            elif run["conclusion"] == "failure":
                failed_runs += 1
                failed_actions.append({
                    "repo": repo_name,
                    "name": run["name"],
                    "url": run["html_url"]
                })
                    # Calculate success rate
        if total_runs > 0:
            success_rate = successful_runs / total_runs * 100
        else:
            success_rate = 0.0
    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "failed_actions": failed_actions,
        "success_rate": success_rate
    }

def get_month():
    last_month = datetime.now().replace(day=1) - timedelta(days=1)
    formatted_month = last_month.strftime("%B %Y")
    return formatted_month

def update_google_sheet(stats):
    """Update Google Sheet with workflow statistics"""
    failed_actions = [f"- {action['repo']}: {action['name']} ({action['url']})" for action in stats["failed_actions"]]
    
    rows = [
        [
            get_month(),
            stats["total_runs"],
            stats["successful_runs"],
            stats["failed_runs"],
            stats["success_rate"],
            "\n".join(failed_actions) if failed_actions else "No failed actions"
        ]
    ]

    # Open the Google Sheet and append the data
    print("Updating Google Sheet...")
    sh = gc.open("Production Reliability Workbook")
    worksheet = sh.worksheet("Infrastructure Automation Pipeline Stability")
    
    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    
    print(f"Successfully updated sheet with {len(rows)} entries.")

def main():
    stats = get_terraform_apply_workflow_stats()
    print(f"Total runs: {stats['total_runs']}")
    print(f"Successful runs: {stats['successful_runs']}")
    print(f"Failed runs: {stats['failed_runs']}")
    print(f"Success rate: {stats['success_rate']}")
    if stats["failed_actions"]:
        print("\nFailed actions:")
        for action in stats["failed_actions"]:
            print(f"- {action['repo']}: {action['name']} ({action['url']})")
    update_google_sheet(stats)

if __name__ == "__main__":
    main()
