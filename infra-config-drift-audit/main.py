"""
This script audits configuration drift across Fincra's infrastructure repositories by comparing the current state of infrastructure code with the deployed state.

Main tasks:
- Loads a list of infrastructure repositories from a YAML configuration file.
- Fetches and compares configuration files or state from source control and deployed environments.
- Identifies and reports any configuration drift.
- Updates a Google Sheet ("Production Reliability Workbook" > "Infra Config Drift Audit") with audit results.

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




org_name = "FincraNG"
repo_name = "fincra-org-infra"
token = os.getenv("FINCRA_GITHUB_TOKEN")
workflow_identifier = "drift-detection.yaml"

# base_url = f"https://api.github.com/repos/{org_name}/{repo_name}/actions/runs"

base_url = f"https://api.github.com/repos/{org_name}/{repo_name}/actions/workflows/{workflow_identifier}/runs"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# Get workflow runs
response = requests.get(base_url, headers=headers)
runs = response.json().get('workflow_runs', [])

# for run in runs:
    # run_id = run['id']
    # print(f"\nWorkflow Run: {run['name']} (ID: {run_id})")
    # print(f"Status: {run['status']}, Conclusion: {run['conclusion']}")
    
    #look at a particular jobs in a run for now
run_id = 15627805994  # Replace with the actual run ID you want to inspect
run_url = f"https://api.github.com/repos/{org_name}/{repo_name}/actions/runs/{run_id}/jobs"
run_response = requests.get(run_url, headers=headers)
run_details = run_response.json().get('jobs', [])
 # Get job name, status and number of jobs
drift_check_jobs = [job for job in run_details if "Check:" in job['name']]
print(f"\nTotal number of Drift Check jobs: {len(drift_check_jobs)}")
print(drift_check_jobs)
# for job in drift_check_jobs:
#     print(f"Job Name: {job['name']}")
#     print(f"Job Status: {job['status']}")
#     print(f"Job Conclusion: {job['conclusion']}")


    # # Get jobs for this run
    # jobs_url = f"{base_url}/{run_id}/jobs"
    # jobs_response = requests.get(jobs_url, headers=headers)
    # jobs = jobs_response.json().get('jobs', [])
    
    # for job in jobs:
    #     print(f"\n  Job: {job['name']}")
    #     print(f"  Status: {job['status']}, Conclusion: {job['conclusion']}")
        
    #     # Print steps (sub-jobs)
    #     for step in job['steps']:
    #         print(f"    Step: {step['name']}")
    #         print(f"    Status: {step['status']}, Conclusion: {step['conclusion']}")