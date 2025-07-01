import boto3, os
import datetime
from datetime import timezone
from dotenv import load_dotenv

load_dotenv()

start_time = datetime.datetime(2025, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
end_time = datetime.datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

def get_temp_credentials():
    sts = boto3.client('sts')
    resp = sts.get_session_token(
       SerialNumber=os.getenv('AWS_MFA_SERIAL'),
       TokenCode=input("Enter MFA code: ")
    )
    return resp['Credentials']


def get_monthly_cost():

    creds = get_temp_credentials()
    os.environ.update({
      'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
      'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
      'AWS_SESSION_TOKEN': creds['SessionToken'],
    })

    client = boto3.client('ce',)

    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_time.strftime('%Y-%m-%d'),
            'End': end_time.strftime('%Y-%m-%d')
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )

    results = response['ResultsByTime'][0]
    amount = results['Total']['UnblendedCost']['Amount']
    unit = results['Total']['UnblendedCost']['Unit']
    print(f"AWS cost for {start_time.year}-{start_time.month:02d}: {amount} {unit}")

if __name__ == "__main__":
    get_monthly_cost()
