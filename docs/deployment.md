# Qenergyz Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Qenergyz platform across different environments and cloud providers.

## Prerequisites

### Required Tools
- **Terraform**: v1.6.0 or later
- **Docker**: v24.0 or later
- **AWS CLI**: v2.0 or later (for AWS deployments)
- **kubectl**: v1.28 or later (for Kubernetes deployments)
- **Node.js**: v20 or later
- **Python**: v3.11 or later

### Access Requirements
- Cloud provider credentials (AWS/GCP/Azure)
- Docker registry access
- GitHub repository access
- Secrets management access

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/akramahmed1/qenergyz.git
cd qenergyz
```

### 2. Configure Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### 3. Set Up Cloud Credentials

#### AWS
```bash
aws configure
# OR
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### GCP
```bash
gcloud auth login
gcloud config set project your-project-id
```

#### Azure
```bash
az login
az account set --subscription your-subscription-id
```

## Infrastructure Deployment

### 1. Initialize Terraform

#### AWS Deployment
```bash
cd infrastructure/terraform/aws
terraform init
```

#### GCP Deployment
```bash
cd infrastructure/terraform/gcp
terraform init
```

#### Azure Deployment
```bash
cd infrastructure/terraform/azure
terraform init
```

### 2. Plan Infrastructure Changes
```bash
terraform plan -var-file="environments/staging.tfvars"
```

### 3. Deploy Infrastructure
```bash
terraform apply -var-file="environments/staging.tfvars"
```

### 4. Verify Deployment
```bash
terraform output
```

## Application Deployment

### 1. Build Docker Images

#### Backend
```bash
cd backend
docker build -t qenergyz/backend:latest .
docker tag qenergyz/backend:latest $ECR_REGISTRY/qenergyz/backend:latest
docker push $ECR_REGISTRY/qenergyz/backend:latest
```

#### Frontend
```bash
cd frontend
npm run build
docker build -t qenergyz/frontend:latest .
docker tag qenergyz/frontend:latest $ECR_REGISTRY/qenergyz/frontend:latest
docker push $ECR_REGISTRY/qenergyz/frontend:latest
```

### 2. Deploy Application Services

#### Using ECS (AWS)
```bash
# Update ECS service
aws ecs update-service \
  --cluster qenergyz-production \
  --service qenergyz-backend \
  --force-new-deployment

aws ecs update-service \
  --cluster qenergyz-production \
  --service qenergyz-frontend \
  --force-new-deployment
```

#### Using GKE (GCP)
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/services.yaml
```

#### Using AKS (Azure)
```bash
# Set AKS context
az aks get-credentials --resource-group qenergyz-rg --name qenergyz-aks

# Deploy application
kubectl apply -f k8s/
```

### 3. Database Migrations
```bash
# Run database migrations
docker run --rm \
  --network qenergyz_default \
  -e DATABASE_URL=postgresql://user:pass@db:5432/qenergyz \
  qenergyz/backend:latest \
  python -m alembic upgrade head
```

### 4. Health Check Verification
```bash
# Check application health
curl -f http://your-load-balancer/health
```

## Deployment Strategies

### Rolling Deployment
- **Use Case**: Regular updates with minimal downtime
- **Process**: Gradually replace instances with new version
- **Rollback**: Quick rollback to previous version

```bash
# Rolling deployment example
aws ecs update-service \
  --cluster qenergyz-production \
  --service qenergyz-backend \
  --deployment-configuration \
  maximumPercent=200,minimumHealthyPercent=50
```

### Blue-Green Deployment
- **Use Case**: Zero-downtime deployments with instant rollback
- **Process**: Deploy to parallel environment, switch traffic
- **Requirements**: Double infrastructure resources temporarily

```bash
# Blue-green deployment script
./scripts/blue-green-deploy.sh production backend v1.2.3
```

### Canary Deployment
- **Use Case**: Gradual rollout with risk mitigation
- **Process**: Deploy to subset of users, monitor, expand
- **Monitoring**: Enhanced monitoring during rollout

```bash
# Canary deployment with 10% traffic
./scripts/canary-deploy.sh production backend v1.2.3 10
```

## Environment-Specific Configurations

### Staging Environment
```bash
# Staging deployment
terraform apply -var-file="environments/staging.tfvars"

# Deploy with staging configuration
docker-compose -f docker-compose.staging.yml up -d
```

### Production Environment
```bash
# Production deployment (requires approval)
terraform apply -var-file="environments/production.tfvars"

# Deploy with production configuration
docker-compose -f docker-compose.production.yml up -d
```

## CI/CD Pipeline

### GitHub Actions Workflow

#### Automatic Deployment
- **Trigger**: Push to main/develop branch
- **Process**: Build → Test → Deploy
- **Approval**: Required for production

#### Manual Deployment
- **Trigger**: GitHub Actions workflow dispatch
- **Options**: Environment and strategy selection
- **Monitoring**: Real-time deployment status

### Pipeline Stages
1. **Security Scan**: SAST, dependency scanning
2. **Build & Test**: Docker image build and testing
3. **Infrastructure**: Terraform plan and apply
4. **Application Deploy**: Container deployment
5. **Health Check**: Post-deployment verification
6. **Notification**: Team notification

## Secrets Management

### AWS Secrets Manager
```bash
# Store secret
aws secretsmanager create-secret \
  --name "qenergyz/production/db-password" \
  --secret-string "your-secure-password"

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id "qenergyz/production/db-password"
```

### Environment Variables
```bash
# Application secrets (never commit to Git)
export DATABASE_URL="postgresql://..."
export JWT_SECRET="your-jwt-secret"
export REDIS_URL="redis://..."
export SENTRY_DSN="https://..."
```

### Secrets Rotation
```bash
# Automated secrets rotation
./scripts/rotate-secrets.sh production
```

## Monitoring Setup

### Application Monitoring
```bash
# Configure Sentry
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ENVIRONMENT="production"

# Configure structured logging
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"
```

### Infrastructure Monitoring
```bash
# CloudWatch agent configuration
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/config.json -s
```

### Custom Dashboards
```bash
# Deploy monitoring dashboards
aws cloudwatch put-dashboard \
  --dashboard-name "Qenergyz-Production" \
  --dashboard-body file://monitoring/dashboard.json
```

## Troubleshooting Deployments

### Common Issues

#### Container Not Starting
```bash
# Check container logs
docker logs qenergyz-backend

# Check ECS service events
aws ecs describe-services \
  --cluster qenergyz-production \
  --services qenergyz-backend
```

#### Database Connection Failed
```bash
# Test database connectivity
docker run --rm -it postgres:15 \
  psql postgresql://user:pass@host:5432/dbname

# Check security groups
aws ec2 describe-security-groups \
  --group-ids sg-xxxxxxxxx
```

#### Load Balancer Health Check Failing
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:...

# Check application health endpoint
curl -v http://your-app/health
```

### Rollback Procedures

#### Immediate Rollback
```bash
# Rollback to previous version
aws ecs update-service \
  --cluster qenergyz-production \
  --service qenergyz-backend \
  --task-definition qenergyz-backend:previous-revision
```

#### Database Rollback
```bash
# Database migration rollback
docker run --rm \
  -e DATABASE_URL=postgresql://... \
  qenergyz/backend:previous \
  python -m alembic downgrade -1
```

## Performance Optimization

### Auto Scaling Configuration
```bash
# Configure ECS auto scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/qenergyz-production/qenergyz-backend \
  --min-capacity 2 \
  --max-capacity 10
```

### CDN Setup
```bash
# Configure CloudFront distribution
aws cloudfront create-distribution \
  --distribution-config file://cdn-config.json
```

## Security Considerations

### Network Security
- All traffic encrypted in transit (TLS 1.3)
- Database in private subnets only
- Security groups restrict access
- VPC Flow Logs enabled

### Application Security
- Container images scanned for vulnerabilities
- Secrets never stored in code
- Regular dependency updates
- OWASP compliance

### Compliance
- SOC 2 controls implemented
- GDPR compliance verified
- Regional requirements met
- Audit logging enabled

## Cost Optimization

### Resource Right-Sizing
```bash
# Monitor resource utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Reserved Instances
- 1-year reserved instances for production
- Spot instances for development
- Scheduled scaling for predictable loads

## Support and Escalation

### Deployment Support
- **Primary Contact**: DevOps Team (devops@qenergyz.com)
- **Secondary Contact**: Infrastructure Team (infra@qenergyz.com)
- **Emergency**: On-call engineer via PagerDuty

### Documentation Updates
- Update this guide after significant changes
- Version control all deployment scripts
- Maintain change log for infrastructure

## Related Documentation

- [Infrastructure Documentation](./infra.md)
- [Security Runbook](../runbooks/security.md)
- [Monitoring Guide](../runbooks/monitoring.md)
- [Incident Response](../runbooks/incident-response.md)