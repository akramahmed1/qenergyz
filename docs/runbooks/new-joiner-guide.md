# New Joiner Onboarding Guide

## Welcome to Qenergyz! 🎉

This guide will help you get up and running with our platform development and operations.

## Day 1: Setup and Access

### 1. Account Setup
- [ ] GitHub access granted to [akramahmed1/qenergyz](https://github.com/akramahmed1/qenergyz)
- [ ] Slack workspace invitation received
- [ ] AWS console access configured
- [ ] Development environment credentials provided

### 2. Development Environment

#### Prerequisites Installation
```bash
# Install required tools (macOS)
brew install terraform docker aws-cli kubectl node python

# Install required tools (Ubuntu/Debian)
sudo apt update
sudo apt install -y curl wget git
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
```

#### Clone and Setup Repository
```bash
# Clone the repository
git clone https://github.com/akramahmed1/qenergyz.git
cd qenergyz

# Copy environment configuration
cp .env.example .env

# Setup Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

#### Local Development Setup
```bash
# Start development services
docker-compose up -d postgres redis

# Run database migrations
cd backend
python -m alembic upgrade head

# Start backend server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend server (in new terminal)
cd frontend
npm run dev
```

#### Verify Setup
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Health Check: http://localhost:8000/health

### 3. Essential Tools Setup

#### IDE Configuration
**Recommended**: VS Code with extensions:
- Python
- Prettier
- ESLint
- Terraform
- Docker
- GitLens

#### AWS CLI Configuration
```bash
aws configure
# Enter your AWS Access Key ID and Secret Access Key
# Default region: us-east-1
# Output format: json
```

#### Git Configuration
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@qenergyz.com"
git config --global pull.rebase false
```

## Day 2-3: Platform Understanding

### 1. Architecture Overview

#### System Components
- **Backend**: FastAPI (Python) - API and business logic
- **Frontend**: React (TypeScript) - User interface
- **Database**: PostgreSQL - Primary data store
- **Cache**: Redis - Session and application cache
- **Message Queue**: Kafka - Event streaming
- **Monitoring**: Sentry - Error tracking and performance

#### Key Directories
```
qenergyz/
├── backend/                 # Python FastAPI backend
│   ├── src/                # Source code
│   ├── tests/              # Test files
│   ├── alembic/            # Database migrations
│   └── requirements.txt    # Python dependencies
├── frontend/               # React TypeScript frontend
│   ├── src/                # Source code
│   ├── public/             # Static assets
│   └── package.json        # Node dependencies
├── infrastructure/         # Infrastructure as Code
│   └── terraform/          # Terraform configurations
├── docs/                   # Documentation
│   ├── infra.md           # Infrastructure docs
│   ├── deployment.md      # Deployment guide
│   └── runbooks/          # Operational runbooks
└── .github/               # CI/CD workflows
    └── workflows/
```

### 2. Development Workflow

#### Git Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature-name
```

#### Code Standards
- **Python**: Black formatting, isort imports, type hints
- **TypeScript**: Prettier formatting, ESLint rules
- **Commits**: Conventional commits (feat:, fix:, docs:, etc.)

#### Testing
```bash
# Backend tests
cd backend
python -m pytest tests/ -v --cov=src

# Frontend tests
cd frontend
npm test
```

### 3. Local Development Tips

#### Database Management
```bash
# Connect to local PostgreSQL
docker exec -it qenergyz_postgres_1 psql -U qenergyzuser -d qenergyz

# View database schema
\dt

# Run specific migration
python -m alembic upgrade +1

# Create new migration
python -m alembic revision --autogenerate -m "add new table"
```

#### Debugging
```bash
# View application logs
docker-compose logs -f backend

# Debug with breakpoints (add to Python code)
import pdb; pdb.set_trace()

# Monitor Redis
docker exec -it qenergyz_redis_1 redis-cli monitor
```

## Week 1: Feature Development

### 1. First Task Assignment
Your mentor will assign a small feature or bug fix to help you understand the codebase.

### 2. Code Review Process
- All changes require code review
- Address reviewer feedback promptly  
- Test your changes thoroughly
- Update documentation if needed

### 3. Common Patterns

#### Backend API Development
```python
# Example API endpoint
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db

router = APIRouter(prefix="/api/v1")

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    # Implementation here
    return {"user_id": user_id}
```

#### Frontend Component Development
```typescript
// Example React component
import React from 'react';
import { useQuery } from '@tanstack/react-query';

interface User {
  id: number;
  name: string;
}

export const UserProfile: React.FC<{ userId: number }> = ({ userId }) => {
  const { data: user, isLoading } = useQuery<User>(['user', userId], () =>
    fetch(`/api/v1/users/${userId}`).then(res => res.json())
  );

  if (isLoading) return <div>Loading...</div>;
  
  return <div>Welcome, {user?.name}!</div>;
};
```

## Week 2: Infrastructure and Operations

### 1. Infrastructure Understanding

#### Cloud Architecture
- **AWS**: Primary production environment
- **Terraform**: Infrastructure as Code
- **ECS**: Container orchestration
- **RDS**: Managed PostgreSQL database
- **ElastiCache**: Managed Redis

#### Environment Access
```bash
# Connect to staging environment
aws ecs execute-command \
  --cluster qenergyz-staging \
  --task arn:aws:ecs:us-east-1:123456789:task/xxx \
  --command "/bin/bash" \
  --interactive
```

### 2. Monitoring and Debugging

#### Application Monitoring
- **Sentry**: https://sentry.io/organizations/qenergyz/
- **AWS CloudWatch**: https://console.aws.amazon.com/cloudwatch/
- **Application Logs**: Available in CloudWatch

#### Key Metrics to Monitor
- Response time and throughput
- Error rates and exceptions
- Database performance
- Infrastructure utilization

#### Debugging Production Issues
```bash
# Check application logs
aws logs filter-log-events \
  --log-group-name "/ecs/qenergyz-production" \
  --filter-pattern "ERROR" \
  --start-time 1640995200000

# Check service health
curl -f https://api.qenergyz.com/health
```

### 3. Deployment Process

#### Staging Deployment
- Automatic on merge to `develop` branch
- Manual approval required for production
- Blue/green deployment strategy for zero downtime

#### Production Deployment
- Triggered by merge to `main` branch
- Requires manual approval
- Comprehensive health checks
- Automatic rollback on failure

## Security and Compliance

### 1. Security Best Practices
- Never commit secrets to Git
- Use environment variables for configuration
- Keep dependencies updated
- Follow OWASP guidelines

### 2. Data Handling
- Encrypt sensitive data at rest and in transit
- Implement proper access controls
- Log security-relevant events
- Regular security scans

### 3. Compliance Requirements
- SOC 2 Type II (in progress)
- GDPR compliance for EU users
- Regional financial regulations

## Getting Help

### 1. Documentation
- [Infrastructure Guide](../infra.md)
- [Deployment Guide](../deployment.md)
- [API Documentation](http://localhost:8000/docs)

### 2. Communication Channels
- **#general**: General discussion
- **#development**: Development questions
- **#infrastructure**: Infrastructure and deployment
- **#security**: Security-related topics
- **#alerts**: Automated alerts and notifications

### 3. Team Contacts
- **Technical Lead**: tech-lead@qenergyz.com
- **DevOps Team**: devops@qenergyz.com
- **Security Team**: security@qenergyz.com
- **Your Mentor**: [Assigned during onboarding]

### 4. Escalation Process
1. **Development Issues**: Ask in Slack #development
2. **Infrastructure Issues**: Contact DevOps team
3. **Security Concerns**: Immediate escalation to security team
4. **Urgent Issues**: On-call engineer via PagerDuty

## Learning Resources

### 1. Technology-Specific
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **Terraform**: https://developer.hashicorp.com/terraform
- **AWS**: https://aws.amazon.com/training/

### 2. Company-Specific
- **Energy Trading**: Internal knowledge base
- **Financial Regulations**: Compliance documentation
- **Business Domain**: Product team documentation

### 3. Best Practices
- **Clean Code**: "Clean Code" by Robert Martin
- **System Design**: "Designing Data-Intensive Applications" by Martin Kleppmann
- **DevOps**: "The DevOps Handbook" by Gene Kim

## 30-60-90 Day Goals

### 30 Days
- [ ] Complete development environment setup
- [ ] Understand system architecture
- [ ] Complete first feature implementation
- [ ] Familiar with deployment process
- [ ] Complete security training

### 60 Days
- [ ] Independently implement medium-complexity features
- [ ] Understand infrastructure and monitoring
- [ ] Contribute to code reviews
- [ ] Handle production issues with guidance
- [ ] Complete domain knowledge training

### 90 Days
- [ ] Lead small feature development
- [ ] Mentor newer team members
- [ ] Contribute to architecture decisions
- [ ] Handle production incidents independently
- [ ] Contribute to process improvements

## Common Troubleshooting

### Development Environment Issues

#### Docker Container Won't Start
```bash
# Check container logs
docker-compose logs backend

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Reset database (WARNING: loses data)
docker-compose down -v
docker-compose up -d postgres
cd backend && python -m alembic upgrade head
```

#### Python Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Production Issues

#### Application Not Responding
1. Check load balancer health checks
2. Review application logs
3. Check database connectivity
4. Verify infrastructure status

#### High Error Rate
1. Check Sentry for error details
2. Review recent deployments
3. Check database performance
4. Verify external service status

---

**Welcome to the team! Don't hesitate to ask questions - we're here to help you succeed!**