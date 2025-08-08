import json
import urllib3
import os

def handler(event, context):
    """
    Lambda function to send CloudWatch alarm notifications to Slack
    """
    webhook_url = os.environ['SLACK_WEBHOOK_URL']
    
    # Parse the SNS message
    message = json.loads(event['Records'][0]['Sns']['Message'])
    
    alarm_name = message['AlarmName']
    alarm_description = message['AlarmDescription']
    new_state = message['NewStateValue']
    reason = message['NewStateReason']
    timestamp = message['StateChangeTime']
    
    # Determine color based on alarm state
    color = {
        'ALARM': '#FF0000',      # Red
        'OK': '#00FF00',         # Green
        'INSUFFICIENT_DATA': '#FFFF00'  # Yellow
    }.get(new_state, '#808080')  # Gray for unknown
    
    # Create Slack message
    slack_message = {
        'text': f'CloudWatch Alarm: {alarm_name}',
        'attachments': [
            {
                'color': color,
                'fields': [
                    {
                        'title': 'Alarm',
                        'value': alarm_name,
                        'short': True
                    },
                    {
                        'title': 'State',
                        'value': new_state,
                        'short': True
                    },
                    {
                        'title': 'Description',
                        'value': alarm_description,
                        'short': False
                    },
                    {
                        'title': 'Reason',
                        'value': reason,
                        'short': False
                    },
                    {
                        'title': 'Time',
                        'value': timestamp,
                        'short': True
                    }
                ]
            }
        ]
    }
    
    # Send to Slack
    http = urllib3.PoolManager()
    response = http.request(
        'POST',
        webhook_url,
        body=json.dumps(slack_message),
        headers={'Content-Type': 'application/json'}
    )
    
    return {
        'statusCode': response.status,
        'body': json.dumps('Notification sent to Slack')
    }