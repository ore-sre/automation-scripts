# NewRelic-metrics-to-sheets

A GitHub Actions workflow that automatically collects performance metrics and error logs from New Relic and stores them in Google Sheets for easy tracking and analysis.

## Overview

This project automates the collection of key performance metrics and error logs from New Relic for multiple services and logs them to a Google Spreadsheet. It runs daily at midnight Nigerian time (WAT) via GitHub Actions, providing a consistent record of application performance without manual intervention.

## Metrics Collected

For each service defined in `services.yml`, the following metrics are collected:

- **Average Response Time**: The average duration of web transactions in milliseconds
- **Error Rate**: The percentage of web transactions that result in errors
- **Throughput**: The average number of requests per second
- **Error Logs**: Top 5 most frequent error messages with counts and timestamps

## Setup

### Prerequisites

- A New Relic account with API access
- A Google account with Google Sheets access
- A GitHub repository to host this workflow


## How It Works

1. The GitHub Actions workflow runs on a daily schedule
2. It sets up a Python environment and installs dependencies
3. It decodes and saves the Google service account credentials
4. It runs two scripts:
   - `fetch_nr.py`: Collects APM performance metrics
   - `fetch_nr_err_logs.py`: Collects error logs with details
5. Each script:
   - Authenticates with New Relic using the API key
   - Queries metrics/logs for each service
   - Connects to Google Sheets using the service account
   - Appends the data to the specified worksheet with timestamps

## Local Development

To run these scripts locally:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with the following variables:
   ```
   NEW_RELIC_API_KEY=your_api_key
   ACCOUNT_ID=your_account_id
   ```
4. Place your Google service account JSON file in the project directory as `service_account.json`
5. Run the scripts:
   - For performance metrics: `python fetch_nr.py`
   - For error logs: `python fetch_nr_err_logs.py`

## Customization

- To change the schedule, edit the cron expression in `.github/workflows/nr_metrics_to_sheets.yml`
- To modify the metrics collected, edit the query functions in `fetch_nr.py`
- To change the error logs collection, edit the query functions in `fetch_nr_err_logs.py`
- To change the spreadsheet format, edit the spreadsheet update code in either script

## Spreadsheet Structure

The data is organized into two worksheets:

1. **APM Metrics Report**: Contains daily performance metrics
   - Timestamp
   - Service name
   - Average response time
   - Error rate
   - Throughput

2. **Error Logs Report**: Contains detailed error logs
   - Timestamp
   - Service name
   - Error message
   - HTTP code
   - Count
   - Percentage of total errors
   - Last seen timestamp

Each day's data is separated by a date header in the format "May 14th 2025".

## Troubleshooting

If the workflow fails, check the GitHub Actions logs for error messages. Common issues include:
- Invalid API credentials
- Incorrect service names in `services.yml`
- Google Sheets permission issues
- New Relic API query format changes

## License

[MIT License](LICENSE)
