#!/bin/bash
# Start script for Qenergyz backend services

# Default environment variables
export SECRET_KEY=${SECRET_KEY:-"development-secret-key-change-in-production"}
export ENCRYPTION_KEY=${ENCRYPTION_KEY:-"development-encryption-key-change-in-production"}
export DATABASE_URL=${DATABASE_URL:-"postgresql+asyncpg://qenergyz:qenergyz123@localhost:5432/qenergyz"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
export ENVIRONMENT=${ENVIRONMENT:-"development"}
export DEBUG=${DEBUG:-"true"}

echo "🚀 Starting Qenergyz Backend Services"
echo "Environment: $ENVIRONMENT"
echo "Database: $DATABASE_URL"

# Check which API to run
API_VERSION=${API_VERSION:-"v2"}

if [ "$API_VERSION" = "v1" ]; then
    echo "Starting Legacy API (v1)..."
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
elif [ "$API_VERSION" = "v2" ]; then
    echo "Starting New API (v2) with Auth & Database..."
    
    # Run database migrations
    echo "Running database migrations..."
    alembic upgrade head || echo "Warning: Migration failed, continuing..."
    
    # Start the new API
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Invalid API_VERSION. Use 'v1' or 'v2'"
    exit 1
fi