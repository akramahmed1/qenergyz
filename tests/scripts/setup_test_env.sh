#!/bin/bash
# Qenergyz Testing Environment Setup Script
set -e

echo "🔧 Setting up Qenergyz Testing Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if we're in the tests directory
if [[ ! -f "conftest.py" ]]; then
    print_error "Please run this script from the tests directory"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d'.' -f1-2)
if [[ ! "$PYTHON_VERSION" > "3.8" ]]; then
    print_error "Python 3.9+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi
print_status "Python version check passed: $PYTHON_VERSION"

# Install Python testing dependencies
print_status "Installing Python testing dependencies..."
pip install -r requirements.txt --user

# Check Docker availability
if command -v docker &> /dev/null; then
    print_status "Docker is available"
    
    # Start required services for testing
    print_status "Starting test services with Docker..."
    docker-compose -f ../docker-compose.yml up -d redis postgres
    sleep 10  # Wait for services to start
else
    print_warning "Docker not found. Some tests may fail."
fi

# Create test database
print_status "Creating test database..."
export DATABASE_URL="sqlite:///./test.db"
if [[ -f "../backend/alembic.ini" ]]; then
    cd ../backend && python -m alembic upgrade head && cd ../tests
    print_status "Database schema created"
else
    print_warning "Alembic not found. Database migrations skipped."
fi

# Check Node.js for frontend tests
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ $NODE_VERSION -ge 18 ]]; then
        print_status "Node.js version check passed: $(node --version)"
        
        # Install frontend testing dependencies
        if [[ -f "../frontend/package.json" ]]; then
            print_status "Installing frontend testing dependencies..."
            cd ../frontend && npm install && cd ../tests
        fi
        
        # Install Playwright browsers
        print_status "Installing Playwright browsers..."
        playwright install --with-deps chromium firefox webkit
    else
        print_warning "Node.js 18+ is required for frontend tests. Current version: $(node --version)"
    fi
else
    print_warning "Node.js not found. Frontend tests will be skipped."
fi

# Install additional testing tools
print_status "Installing additional testing tools..."

# Install k6 for load testing
if ! command -v k6 &> /dev/null; then
    print_status "Installing k6 for load testing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo gpg -k
        sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
        sudo apt-get update
        sudo apt-get install k6
    else
        print_warning "k6 installation skipped. Please install manually for load testing."
    fi
fi

# Setup environment variables
print_status "Setting up environment variables..."
cat > .env.test << EOF
# Test environment configuration
TESTING=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./test.db
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=test-secret-key-for-testing-only
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# External service mocks
MOCK_EXTERNAL_APIS=true
MOCK_PAYMENT_GATEWAY=true
MOCK_COMPLIANCE_SERVICE=true

# Test data settings
USE_TEST_DATA=true
RESET_DB_ON_START=true
EOF

# Create test data directory
mkdir -p test_data/{fixtures,mocks,reports}
print_status "Created test data directories"

# Setup test reporting
print_status "Setting up test reporting..."
mkdir -p reports/{html,allure,coverage,performance,security}

# Verify setup
print_status "Verifying test environment setup..."

# Check if pytest works
if python -m pytest --version &> /dev/null; then
    print_status "Pytest is working correctly"
else
    print_error "Pytest installation failed"
    exit 1
fi

# Check if services are running
if command -v docker &> /dev/null; then
    if docker ps | grep -q redis; then
        print_status "Redis service is running"
    else
        print_warning "Redis service is not running. Some tests may fail."
    fi
    
    if docker ps | grep -q postgres; then
        print_status "PostgreSQL service is running"
    else
        print_warning "PostgreSQL service is not running. Some tests may fail."
    fi
fi

print_status "✨ Test environment setup completed!"
echo ""
echo "🚀 Next steps:"
echo "   1. Run smoke tests: pytest 1_smoke/ -v"
echo "   2. Run all tests: ./scripts/run_all_tests.sh"
echo "   3. Check test coverage: pytest --cov=../backend/src tests/"
echo ""
echo "📊 Test reports will be generated in: reports/"
echo "🔧 Test configuration: .env.test"