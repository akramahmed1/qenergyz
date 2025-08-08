# Qenergyz Backend API

Advanced Energy Trading and Risk Management (ETRM) Backend API with comprehensive authentication, database integration, and security features.

## 🚀 Features

### Core API Features
- **FastAPI Framework** - High-performance async API with automatic OpenAPI documentation
- **JWT Authentication** - Access/refresh tokens with role-based access control (RBAC)
- **Database Integration** - SQLAlchemy async models with PostgreSQL/SQLite support
- **Rate Limiting** - Redis-backed rate limiting with user-specific limits
- **Input Validation** - Comprehensive validation and sanitization
- **Audit Logging** - Complete audit trail for compliance
- **Security** - Brute force protection, password policies, CORS, security headers

### Authentication & Security
- **Password Security** - Argon2 hashing with bcrypt fallback
- **Multi-Factor Auth** - Ready for MFA integration
- **Session Management** - Secure session tracking and invalidation
- **Brute Force Protection** - Account lockout after failed attempts
- **Password Policies** - Strong password requirements with validation

### Database Models
- **User Management** - Complete user model with RBAC
- **Audit Logging** - Comprehensive audit trails
- **Session Tracking** - Security-focused session management
- **Alembic Migrations** - Database version control

### API Endpoints

#### Authentication (`/api/v1/auth/`)
- `POST /register` - User registration with validation
- `POST /login` - JWT authentication with brute force protection  
- `POST /logout` - Session invalidation
- `GET /me` - Current user information
- `POST /change-password` - Secure password updates

#### User Management (`/api/v1/users/`)
- `GET /profile` - User profile information
- `GET /list` - List all users (admin only)

#### Trading (`/api/v1/trading/`)
- `GET /positions` - Trading positions
- `POST /orders` - Create trading orders
- `GET /orders` - List trading orders

#### Other Modules
- **Onboarding** (`/api/v1/onboarding/`) - KYC and account setup
- **Compliance** (`/api/v1/compliance/`) - Regulatory compliance
- **Risk Management** (`/api/v1/risk/`) - Risk monitoring and limits

### Utility Endpoints
- `GET /health` - Application health check
- `GET /api/v1/status` - API status and features
- `GET /api/docs` - OpenAPI documentation
- `GET /api/redoc` - ReDoc documentation

## 🛠 Setup

### Environment Variables

Create a `.env` file with:

```bash
# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# Database  
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/qenergyz
# For SQLite: DATABASE_URL=sqlite+aiosqlite:///./qenergyz.db

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Application
ENVIRONMENT=development
DEBUG=true
API_VERSION=v2

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=3600
```

### Installation

1. **Install Dependencies**:
```bash
cd backend
pip install -r api-requirements.txt
```

2. **Database Setup**:
```bash
# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_db.py
```

3. **Start the API**:
```bash
# Using the start script
./start.sh

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Setup

```bash
# Build and start all services
docker-compose up --build

# Start just the backend
docker-compose up qenergyz-backend postgres redis
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/api/ -v

# Run specific test categories
pytest tests/api/test_auth.py -v          # Authentication tests  
pytest tests/api/test_basic.py -v         # Basic utility tests
pytest tests/api/test_integration.py -v   # Integration tests

# Run with coverage
pytest tests/api/ --cov=api --cov-report=html
```

### Test Users (Development)

After running the seed script:

```
Admin: admin@qenergyz.com / AdminPassword123!
Trader: trader@qenergyz.com / TraderPassword123!  
Manager: manager@qenergyz.com / ManagerPassword123!
User: user@qenergyz.com / UserPassword123!
```

**⚠️ Change these passwords in production!**

## 📖 API Documentation

Once running, visit:
- **OpenAPI Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

## 🔒 Security Features

### Authentication
- JWT access/refresh tokens
- Argon2 password hashing with bcrypt fallback
- Brute force protection with account lockout
- Session tracking and management
- API key authentication support

### Input Validation  
- Pydantic model validation
- HTML sanitization
- Email and phone validation
- SQL injection prevention
- XSS protection

### Security Headers
- CORS configuration
- Trusted host validation  
- HTTPS redirect (production)
- Rate limiting by user/IP
- Request size limits

### Audit & Compliance
- Complete audit logging
- Security event tracking
- Data privacy logging (GDPR)
- Compliance check logging
- Trade activity logging

## 🏗 Architecture

### Project Structure
```
backend/
├── api/                    # New API structure
│   ├── dependencies/       # Dependency injection
│   │   ├── auth.py        # Authentication
│   │   ├── database.py    # Database sessions
│   │   ├── rate_limiting.py # Rate limiting
│   │   ├── validation.py  # Input validation
│   │   └── logging.py     # Audit logging
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py        # User models
│   │   ├── audit_log.py   # Audit models
│   │   └── database.py    # Database config
│   ├── routes/            # API endpoints
│   │   ├── auth.py        # Authentication
│   │   ├── users.py       # User management
│   │   ├── trading.py     # Trading operations
│   │   └── ...
│   ├── schemas/           # Pydantic schemas
│   ├── utils/             # Utilities
│   └── main.py           # FastAPI application
├── scripts/               # Database scripts
├── tests/                 # Test suite
└── alembic/              # Database migrations
```

### Key Design Patterns
- **Dependency Injection** - Clean separation of concerns
- **Repository Pattern** - Database abstraction
- **Factory Pattern** - Configuration management
- **Observer Pattern** - Event logging
- **Strategy Pattern** - Multiple auth methods

## 🌟 Role-Based Access Control (RBAC)

### User Roles
- **Viewer** - Read-only access
- **User** - Basic user operations
- **Trader** - Trading operations
- **Manager** - Team management
- **Admin** - System administration  
- **Super Admin** - Full system access

### Permission System
- Route-level protection with `@require_roles`
- Endpoint-specific permissions
- Resource-based access control
- Audit trail for all actions

## 🔄 API Versioning

The API supports both legacy (v1) and new (v2) versions:

- **Legacy API** - Original structure in `backend/src/`
- **New API** - Enhanced structure in `backend/api/`
- Set `API_VERSION=v1` or `API_VERSION=v2` environment variable

## 📈 Monitoring & Observability

### Logging
- Structured logging with correlation IDs
- Request/response logging
- Error tracking with stack traces
- Performance metrics

### Health Checks
- Application health endpoints
- Database connectivity checks
- External service monitoring
- Dependency health status

### Metrics
- Request rates and response times
- Authentication success/failure rates
- Error rates by endpoint
- Resource utilization

## 🚀 Deployment

### Production Checklist
- [ ] Update default passwords
- [ ] Configure production database
- [ ] Set up Redis cluster
- [ ] Enable HTTPS
- [ ] Configure monitoring
- [ ] Set up backup procedures
- [ ] Review security settings
- [ ] Load testing

### Environment Configuration
- **Development** - SQLite, local Redis, debug enabled
- **Staging** - PostgreSQL, Redis cluster, rate limiting
- **Production** - High availability, monitoring, security hardening

## 🤝 Contributing

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation
4. Ensure security best practices
5. Run the full test suite

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.