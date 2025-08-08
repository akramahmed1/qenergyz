"""
Simplified FastAPI app for testing basic functionality
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Set environment variables for testing
os.environ.setdefault("SECRET_KEY", "test_secret_key")
os.environ.setdefault("ENCRYPTION_KEY", "test_encryption_key") 
os.environ.setdefault("DB_URL", "sqlite:///test.db")

# Import after setting environment
import sys
sys.path.append('backend')

from src.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    print("🚀 Starting Qenergyz application")
    yield
    print("🛑 Shutting down Qenergyz application")

# Create FastAPI application
app = FastAPI(
    title="Qenergyz ETRM Platform",
    description="Advanced Energy Trading and Risk Management SaaS",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get settings
settings = get_settings()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Qenergyz ETRM Platform",
        "version": "1.0.0",
        "region": settings.region.value,
        "environment": settings.environment.value
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "version": "1.0.0",
        "environment": settings.environment.value
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)