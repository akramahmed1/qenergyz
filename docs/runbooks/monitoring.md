# Monitoring and Incident Response Runbook

## Overview
This runbook provides comprehensive monitoring and incident response procedures for the Qenergyz platform.

## Monitoring Stack

### Cloud-Native Monitoring
- **AWS**: CloudWatch, X-Ray
- **GCP**: Cloud Monitoring, Cloud Logging
- **Azure**: Azure Monitor, Application Insights

### Application Monitoring
- **Sentry**: Error tracking and performance monitoring
- **Custom Metrics**: Business and application-specific metrics
- **Health Checks**: Automated endpoint monitoring

### Infrastructure Monitoring
- **System Metrics**: CPU, memory, disk, network
- **Container Metrics**: Docker/Kubernetes resource usage
- **Database Metrics**: Connection pools, query performance
- **Cache Metrics**: Redis performance and hit rates

## Key Metrics and Thresholds

### Application Metrics

#### Response Time
- **Target**: < 200ms for 95th percentile
- **Warning**: > 500ms
- **Critical**: > 1000ms

```bash
# Query response time metrics (AWS)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=qenergyz-production-alb \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

#### Error Rate
- **Target**: < 0.1%
- **Warning**: > 1%
- **Critical**: > 5%

```bash
# Query error rate metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=qenergyz-production-alb \
  --start-time 2024-01-15T10:00:00Z \
  --end-time 2024-01-15T11:00:00Z \
  --period 300 \
  --statistics Sum
```

#### Throughput
- **Normal**: 100-1000 req/min
- **Warning**: < 50 req/min (potential issues)
- **Critical**: < 10 req/min (service degradation)

### Infrastructure Metrics

#### CPU Utilization
- **Target**: < 70%
- **Warning**: > 80%
- **Critical**: > 90%

#### Memory Utilization
- **Target**: < 80%
- **Warning**: > 85%
- **Critical**: > 95%

#### Database Metrics
- **CPU**: < 75%
- **Connections**: < 80% of max
- **Read/Write Latency**: < 10ms

## Alerting Configuration

### Alert Severity Levels

#### Critical (P0)
- Service completely down
- Data corruption
- Security breach
- **Response**: Immediate (5 minutes)
- **Escalation**: PagerDuty → On-call engineer

#### High (P1)
- Degraded performance
- High error rates
- Database issues
- **Response**: 15 minutes
- **Escalation**: Slack → Team lead

#### Medium (P2)
- Resource constraints
- Capacity warnings
- **Response**: 2 hours
- **Escalation**: Email → Team

#### Low (P3)
- Informational alerts
- Trend notifications
- **Response**: Next business day
- **Escalation**: Dashboard

### Alert Rules

#### Application Alerts
```yaml
# Example CloudWatch alarm configuration
HighErrorRate:
  MetricName: HTTPCode_Target_5XX_Count
  Namespace: AWS/ApplicationELB
  Threshold: 10
  ComparisonOperator: GreaterThanThreshold
  EvaluationPeriods: 2
  Period: 300
  Statistic: Sum
  AlarmActions:
    - !Ref CriticalAlertsTopicArn

HighResponseTime:
  MetricName: TargetResponseTime
  Namespace: AWS/ApplicationELB
  Threshold: 1.0
  ComparisonOperator: GreaterThanThreshold
  EvaluationPeriods: 2
  Period: 300
  Statistic: Average
  AlarmActions:
    - !Ref HighAlertsTopicArn
```

#### Infrastructure Alerts
```yaml
HighCPUUtilization:
  MetricName: CPUUtilization
  Namespace: AWS/ECS
  Threshold: 80
  ComparisonOperator: GreaterThanThreshold
  EvaluationPeriods: 2
  Period: 300
  Statistic: Average
  Dimensions:
    ServiceName: qenergyz-backend
  AlarmActions:
    - !Ref HighAlertsTopicArn

DatabaseHighCPU:
  MetricName: CPUUtilization
  Namespace: AWS/RDS
  Threshold: 75
  ComparisonOperator: GreaterThanThreshold
  EvaluationPeriods: 2
  Period: 300
  Statistic: Average
  Dimensions:
    DBInstanceIdentifier: qenergyz-production-db
  AlarmActions:
    - !Ref MediumAlertsTopicArn
```

## Monitoring Dashboards

### Executive Dashboard
- **Purpose**: High-level business metrics
- **Audience**: Leadership, product management
- **Metrics**:
  - Active users
  - Transaction volume
  - Revenue metrics
  - Service availability

### Operations Dashboard
- **Purpose**: Technical operations
- **Audience**: DevOps, infrastructure team
- **Metrics**:
  - System health
  - Performance metrics
  - Error rates
  - Infrastructure utilization

### Development Dashboard
- **Purpose**: Application performance
- **Audience**: Development team
- **Metrics**:
  - API response times
  - Error tracking
  - Code deployment metrics
  - Feature usage

### Custom Dashboard Creation

#### AWS CloudWatch
```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "Qenergyz-Custom" \
  --dashboard-body file://dashboard-config.json
```

#### Grafana Dashboard (if using)
```json
{
  "dashboard": {
    "title": "Qenergyz Application Metrics",
    "panels": [
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(http_request_duration_seconds)",
            "legendFormat": "Average Response Time"
          }
        ]
      }
    ]
  }
}
```

## Incident Response Procedures

### Incident Severity Classification

#### P0 - Critical
- **Impact**: Complete service outage
- **Examples**:
  - Application completely down
  - Database unavailable
  - Security breach
- **Response Time**: 5 minutes
- **Escalation**: Immediate PagerDuty alert

#### P1 - High
- **Impact**: Significant service degradation
- **Examples**:
  - High error rates (>5%)
  - Slow response times (>2s)
  - Partial functionality loss
- **Response Time**: 15 minutes
- **Escalation**: Slack notification + email

#### P2 - Medium
- **Impact**: Minor service issues
- **Examples**:
  - Elevated resource usage
  - Non-critical component failure
  - Performance degradation
- **Response Time**: 2 hours
- **Escalation**: Email notification

### Incident Response Steps

#### 1. Detection and Alerting (0-5 minutes)
- Monitor alert channels (Slack, PagerDuty, email)
- Acknowledge the incident
- Begin initial assessment

#### 2. Initial Assessment (5-15 minutes)
```bash
# Quick health check
curl -f https://api.qenergyz.com/health

# Check system status
aws ecs describe-services \
  --cluster qenergyz-production \
  --services qenergyz-backend

# Review recent deployments
aws ecs list-tasks \
  --cluster qenergyz-production \
  --service qenergyz-backend
```

#### 3. Communication (15-30 minutes)
- Update incident channel (#incident-response)
- Notify stakeholders
- Create status page update (if external impact)

#### 4. Investigation and Resolution (30+ minutes)
- Gather logs and metrics
- Identify root cause
- Implement fix or rollback
- Monitor resolution

#### 5. Post-Incident Review (24-48 hours)
- Document incident timeline
- Perform root cause analysis
- Identify action items
- Update procedures

### Common Incident Types and Responses

#### High Error Rate
```bash
# 1. Check application logs
aws logs filter-log-events \
  --log-group-name "/ecs/qenergyz-production" \
  --filter-pattern "ERROR" \
  --start-time $(date -d "1 hour ago" +%s)000

# 2. Check external dependencies
curl -f https://api.external-service.com/health

# 3. Review recent deployments
aws ecs describe-services \
  --cluster qenergyz-production \
  --services qenergyz-backend \
  --query 'services[0].deployments'
```

#### High Response Time
```bash
# 1. Check database performance
aws rds describe-db-instances \
  --db-instance-identifier qenergyz-production-db \
  --query 'DBInstances[0].DBInstanceStatus'

# 2. Check cache performance
aws elasticache describe-cache-clusters \
  --cache-cluster-id qenergyz-production-redis

# 3. Check CPU/Memory usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=qenergyz-backend \
  --start-time $(date -d "1 hour ago" --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average
```

#### Database Connection Issues
```bash
# 1. Check database connectivity
nc -zv qenergyz-production-db.cluster-xxx.us-east-1.rds.amazonaws.com 5432

# 2. Check connection pool status
redis-cli -h production-redis.cache.amazonaws.com GET db_connections

# 3. Restart application if needed
aws ecs update-service \
  --cluster qenergyz-production \
  --service qenergyz-backend \
  --force-new-deployment
```

## Monitoring Tools Usage

### Sentry Error Tracking

#### Setup
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://your-dsn@sentry.io/project-id",
    integrations=[FastApiIntegration(auto_enabling_integrations=False)],
    traces_sample_rate=0.1,
    environment="production"
)
```

#### Common Sentry Queries
- Error frequency by endpoint
- Performance issues by transaction
- User impact analysis
- Release comparisons

### Custom Metrics

#### Application Metrics
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def send_custom_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='Qenergyz/Application',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': 'production'
                    }
                ]
            }
        ]
    )
```

#### Business Metrics
```python
# Track user actions
send_custom_metric('UserRegistration', 1)
send_custom_metric('TradeExecuted', trade_value, 'None')
send_custom_metric('APICallsPerMinute', api_calls)
```

## Log Management

### Log Aggregation
- **AWS**: CloudWatch Logs
- **GCP**: Cloud Logging
- **Azure**: Azure Monitor Logs

### Log Retention Policies
- **Production**: 30 days
- **Staging**: 7 days
- **Development**: 3 days

### Log Query Examples

#### Application Errors
```bash
# AWS CloudWatch Insights
aws logs start-query \
  --log-group-name "/ecs/qenergyz-production" \
  --start-time $(date -d "1 hour ago" +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 100'
```

#### Performance Analysis
```bash
# Query slow requests
aws logs start-query \
  --log-group-name "/ecs/qenergyz-production" \
  --start-time $(date -d "1 hour ago" +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, response_time, endpoint | filter response_time > 1000 | sort response_time desc'
```

## Capacity Planning

### Resource Monitoring
- Track usage trends over time
- Identify seasonal patterns
- Plan for growth projections

### Scaling Thresholds
- **Scale Up**: CPU > 70% for 10 minutes
- **Scale Down**: CPU < 30% for 30 minutes
- **Database**: Connection pool > 80%

### Cost Optimization
- Monitor unused resources
- Right-size instances based on utilization
- Use reserved instances for predictable workloads

## Regular Maintenance

### Daily Tasks
- [ ] Review overnight alerts
- [ ] Check system health dashboards
- [ ] Verify backup completion
- [ ] Monitor error rates

### Weekly Tasks
- [ ] Review performance trends
- [ ] Update alert thresholds if needed
- [ ] Check capacity utilization
- [ ] Review security alerts

### Monthly Tasks
- [ ] Review incident reports
- [ ] Update monitoring documentation
- [ ] Optimize alert configurations
- [ ] Capacity planning review

## Contact Information

### Internal Teams
- **DevOps Team**: devops@qenergyz.com
- **Security Team**: security@qenergyz.com
- **Development Team**: dev-team@qenergyz.com

### External Services
- **AWS Support**: Enterprise support case
- **Sentry Support**: support@sentry.io
- **PagerDuty**: Account support

### Emergency Contacts
- **On-call Engineer**: +1-XXX-XXX-XXXX
- **Team Lead**: +1-XXX-XXX-XXXX
- **CTO**: +1-XXX-XXX-XXXX

---

*This runbook should be reviewed and updated monthly or after significant infrastructure changes.*