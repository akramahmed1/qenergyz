import json
import urllib3
import boto3
import os
from datetime import datetime

def handler(event, context):
    """
    Lambda function to perform health checks and send alerts if unhealthy
    """
    health_check_url = os.environ['HEALTH_CHECK_URL']
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    
    # Create HTTP client
    http = urllib3.PoolManager()
    
    # Create CloudWatch and SNS clients
    cloudwatch = boto3.client('cloudwatch')
    sns = boto3.client('sns')
    
    try:
        # Perform health check
        start_time = datetime.now()
        response = http.request('GET', health_check_url, timeout=10)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds() * 1000  # in milliseconds
        is_healthy = response.status == 200
        
        # Send custom metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace='Qenergyz/HealthCheck',
            MetricData=[
                {
                    'MetricName': 'ResponseTime',
                    'Value': response_time,
                    'Unit': 'Milliseconds',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'HealthStatus',
                    'Value': 1 if is_healthy else 0,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        if not is_healthy:
            # Send alert
            message = {
                'AlarmName': 'Application Health Check Failed',
                'AlarmDescription': f'Health check failed with status code: {response.status}',
                'NewStateValue': 'ALARM',
                'NewStateReason': f'HTTP {response.status} response from {health_check_url}',
                'StateChangeTime': datetime.utcnow().isoformat()
            }
            
            sns.publish(
                TopicArn=sns_topic_arn,
                Message=json.dumps(message),
                Subject='Application Health Check Failed'
            )
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'healthy': is_healthy,
                'response_time_ms': response_time,
                'status_code': response.status
            })
        }
        
    except Exception as e:
        # Health check failed due to exception
        cloudwatch.put_metric_data(
            Namespace='Qenergyz/HealthCheck',
            MetricData=[
                {
                    'MetricName': 'HealthStatus',
                    'Value': 0,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        # Send alert
        message = {
            'AlarmName': 'Application Health Check Failed',
            'AlarmDescription': f'Health check failed with exception: {str(e)}',
            'NewStateValue': 'ALARM',
            'NewStateReason': f'Exception during health check: {str(e)}',
            'StateChangeTime': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(message),
            Subject='Application Health Check Failed'
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'healthy': False,
                'error': str(e)
            })
        }