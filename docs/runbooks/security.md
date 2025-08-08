# Security Incident Response Runbook

## Overview
This runbook provides step-by-step procedures for responding to security incidents in the Qenergyz platform.

## Incident Classification

### Severity Levels

#### Critical (P0)
- **Response Time**: Immediate (5 minutes)
- **Examples**: Data breach, system compromise, customer data exposure
- **Actions**: All hands on deck, executive notification

#### High (P1)
- **Response Time**: 15 minutes
- **Examples**: Unauthorized access attempts, service disruption
- **Actions**: Security team lead, on-call engineer

#### Medium (P2)
- **Response Time**: 2 hours
- **Examples**: Suspicious activity, failed penetration attempts
- **Actions**: Standard security team response

#### Low (P3)
- **Response Time**: 24 hours
- **Examples**: Policy violations, minor security alerts
- **Actions**: Log and monitor, no immediate action required

## Initial Response

### 1. Detection and Assessment (0-15 minutes)

#### Identify the Incident
```bash
# Check security monitoring dashboard
curl -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/organizations/qenergyz/events/"

# Review CloudWatch security metrics
aws logs filter-log-events \
  --log-group-name "/aws/waf/qenergyz" \
  --filter-pattern "BLOCK"
```

#### Document Initial Findings
- Time of detection
- Source of detection (automated/manual)
- Initial scope assessment
- Affected systems/users

### 2. Containment (15-30 minutes)

#### Immediate Actions
```bash
# Block suspicious IP addresses
aws wafv2 update-ip-set \
  --id suspicious-ips \
  --addresses "192.168.1.100/32,10.0.0.50/32"

# Disable compromised user accounts
aws cognito-idp admin-disable-user \
  --user-pool-id us-east-1_xxxxxxx \
  --username suspicious-user
```

#### Network Isolation
```bash
# Update security groups to isolate affected instances
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 22 \
  --source-group sg-yyyyyyyyy
```

### 3. Communication (30-60 minutes)

#### Internal Notifications
- Security team via Slack: #security-incidents
- Leadership team: security@qenergyz.com
- Legal team (if data involved): legal@qenergyz.com

#### External Communications
- Customer notification (if required)
- Regulatory reporting (if required)
- Public disclosure (if required)

## Investigation Procedures

### 1. Evidence Preservation

#### Log Collection
```bash
# Collect application logs
aws logs create-export-task \
  --log-group-name "/ecs/qenergyz-production" \
  --from 1640995200000 \
  --to 1641081600000 \
  --destination "s3://qenergyz-security-logs"

# Collect VPC flow logs
aws ec2 describe-flow-logs \
  --filter Name=resource-id,Values=vpc-xxxxxxxxx
```

#### System Snapshots
```bash
# Create EBS snapshots of affected instances
aws ec2 create-snapshot \
  --volume-id vol-xxxxxxxxx \
  --description "Security incident evidence $(date)"

# Export RDS snapshots for analysis
aws rds create-db-snapshot \
  --db-snapshot-identifier incident-$(date +%Y%m%d) \
  --db-instance-identifier qenergyz-production-db
```

### 2. Timeline Reconstruction

#### Log Analysis
```bash
# Search for suspicious activity patterns
grep -r "failed login" /var/log/application/ | tail -100

# Check database access logs
aws rds download-db-log-file-portion \
  --db-instance-identifier qenergyz-production-db \
  --log-file-name postgresql/postgresql.log.2024-01-15-12
```

#### User Activity Review
```bash
# Review user sessions
redis-cli -h production-redis.cache.amazonaws.com \
  KEYS "session:*" | head -50

# Check API access patterns
aws logs filter-log-events \
  --log-group-name "/aws/apigateway/qenergyz" \
  --filter-pattern "{ $.ip = \"suspicious-ip\" }"
```

### 3. Impact Assessment

#### Data Exposure Check
```bash
# Check for unauthorized data access
grep -r "SELECT \* FROM users" /var/log/application/

# Review sensitive API endpoints
aws logs filter-log-events \
  --log-group-name "/ecs/qenergyz-production" \
  --filter-pattern "{ $.endpoint = \"/api/users/*\" && $.method = \"GET\" }"
```

#### System Integrity Verification
```bash
# Check file integrity
find /opt/qenergyz -type f -exec sha256sum {} \; > current-hashes.txt
diff baseline-hashes.txt current-hashes.txt

# Verify container images
docker trust inspect qenergyz/backend:latest
```

## Eradication and Recovery

### 1. Remove Threats

#### Malware Removal
```bash
# Scan containers for malware
clamav-daemon --scan-archive=yes /var/lib/docker/

# Update container images with patches
docker pull qenergyz/backend:latest-patched
docker service update --image qenergyz/backend:latest-patched qenergyz_backend
```

#### Close Security Gaps
```bash
# Update firewall rules
aws ec2 revoke-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

# Rotate compromised credentials
aws secretsmanager update-secret \
  --secret-id qenergyz/production/db-password \
  --secret-string "$(openssl rand -base64 32)"
```

### 2. System Recovery

#### Service Restoration
```bash
# Restore services from clean backups
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier qenergyz-clean-restore \
  --db-snapshot-identifier clean-snapshot-20240115

# Update DNS to point to clean environment
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch file://dns-restore.json
```

#### Data Recovery
```bash
# Restore from backup if data corruption detected
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier qenergyz-production-db \
  --target-db-instance-identifier qenergyz-restored-db \
  --restore-time 2024-01-15T10:00:00.000Z
```

## Post-Incident Activities

### 1. Monitoring Enhancement

#### Implement Additional Controls
```bash
# Add new WAF rules based on attack patterns
aws wafv2 create-rule-group \
  --name QenergySecurityRules \
  --scope CLOUDFRONT \
  --capacity 100 \
  --rules file://new-security-rules.json
```

#### Update Alerting
```bash
# Create new CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "SuspiciousLoginPattern" \
  --alarm-description "Multiple failed logins from same IP" \
  --metric-name FailedLogins \
  --namespace Qenergyz/Security \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### 2. Documentation

#### Incident Report Template
```markdown
# Security Incident Report

**Incident ID**: SEC-2024-001
**Date**: 2024-01-15
**Severity**: Critical
**Status**: Resolved

## Summary
Brief description of the incident

## Timeline
- 10:00 UTC: Initial detection
- 10:05 UTC: Containment initiated
- 10:30 UTC: Stakeholders notified
- 12:00 UTC: Threat eradicated
- 14:00 UTC: Services restored

## Impact
- Affected users: X
- Data exposure: Yes/No
- Service downtime: X minutes
- Financial impact: $X

## Root Cause
Technical details of how the incident occurred

## Lessons Learned
- What went well
- What could be improved
- Preventive measures

## Action Items
- [ ] Update security policies
- [ ] Enhance monitoring
- [ ] Staff training
```

### 3. Lessons Learned Session

#### Team Review Meeting
- Schedule within 72 hours of resolution
- Include all stakeholders
- Focus on improvement, not blame
- Document action items with owners

#### Process Improvements
- Update incident response procedures
- Enhance detection capabilities
- Improve communication protocols
- Schedule security training

## Emergency Contacts

### Internal Team
- **Security Team Lead**: security-lead@qenergyz.com
- **CISO**: ciso@qenergyz.com
- **DevOps On-call**: +1-XXX-XXX-XXXX
- **Legal Team**: legal@qenergyz.com

### External Contacts
- **Cyber Insurance**: +1-XXX-XXX-XXXX
- **Law Enforcement**: FBI IC3 (if applicable)
- **Security Firm**: incident-response@securityfirm.com
- **Public Relations**: pr@qenergyz.com

## Tools and Resources

### Security Tools
- **SIEM**: Splunk/ELK Stack
- **Vulnerability Scanner**: Nessus/OpenVAS
- **Forensics**: SANS SIFT/Volatility
- **Network Analysis**: Wireshark/tcpdump

### Reference Materials
- [NIST Incident Response Guide](https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final)
- [SANS Incident Response Process](https://www.sans.org/white-papers/33901/)
- [Qenergyz Security Policies](./security-policies.md)

## Regular Drills

### Tabletop Exercises
- **Frequency**: Quarterly
- **Participants**: Security team, leadership, legal
- **Scenarios**: Various incident types
- **Duration**: 2-4 hours

### Technical Drills
- **Frequency**: Monthly
- **Focus**: Tool familiarity, process verification
- **Participants**: Technical team
- **Documentation**: Update procedures based on findings

## Compliance Requirements

### Regulatory Reporting
- **SOC 2**: Report within 24 hours
- **GDPR**: Report within 72 hours (if personal data involved)
- **Financial Regulations**: Immediate reporting for trading disruptions

### Customer Notification
- **Timeline**: Within 24 hours for data breaches
- **Method**: Email, in-app notification, website notice
- **Content**: Factual, action-oriented, contact information

---

*This runbook should be reviewed and updated quarterly or after each significant incident.*