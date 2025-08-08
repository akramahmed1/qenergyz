"""
Smoke Tests - Basic Application and Service Health Checks
Tests the fundamental functionality and availability of core services.
"""
import os
import time
import asyncio
import pytest
import psutil
from unittest.mock import Mock, patch


@pytest.mark.smoke
def test_environment_setup():
    """Test that the testing environment is properly configured."""
    # Check required environment variables
    assert os.getenv("TESTING") == "true"
    assert os.getenv("DATABASE_URL") is not None
    assert os.getenv("SECRET_KEY") is not None
    
    # Verify we're not in production
    assert os.getenv("ENVIRONMENT", "test") != "production"


@pytest.mark.smoke
def test_python_dependencies():
    """Test that critical Python dependencies are available."""
    try:
        import fastapi
        import pydantic
        import sqlalchemy
        import asyncio
        import json
    except ImportError as e:
        pytest.fail(f"Critical dependency missing: {e}")
    
    # Check Python version
    import sys
    assert sys.version_info >= (3, 8), "Python 3.8+ required"


@pytest.mark.smoke
def test_system_resources():
    """Test that system has adequate resources for testing."""
    # Check available memory (at least 1GB)
    memory = psutil.virtual_memory()
    available_gb = memory.available / (1024**3)
    assert available_gb >= 1.0, f"Insufficient memory: {available_gb:.1f}GB available"
    
    # Check disk space (at least 5GB)
    disk = psutil.disk_usage('/')
    free_gb = disk.free / (1024**3)
    assert free_gb >= 5.0, f"Insufficient disk space: {free_gb:.1f}GB available"


@pytest.mark.smoke
def test_mock_application_startup():
    """Test that the application can start up successfully."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Create a minimal FastAPI app for testing
    app = FastAPI(title="Qenergyz Test API")
    
    @app.get("/")
    def root():
        return {"message": "Qenergyz API is running", "status": "ok"}
    
    # Test application creation
    assert app.title == "Qenergyz Test API"
    
    # Test client can connect
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Qenergyz" in data["message"]


@pytest.mark.smoke
def test_database_connection_mock():
    """Test database connection establishment (mocked for smoke test)."""
    # Mock database connection for smoke test
    with patch('asyncpg.connect') as mock_connect:
        mock_conn = Mock()
        mock_conn.execute = Mock(return_value=None)
        mock_connect.return_value = mock_conn
        
        # Simulate connection test
        try:
            # This would normally connect to the database
            connection = mock_connect("postgresql://test")
            assert connection is not None
            mock_connect.assert_called_once()
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")


@pytest.mark.smoke
def test_configuration_loading():
    """Test that application configuration loads correctly."""
    # Test environment-based configuration
    config = {
        "database_url": os.getenv("DATABASE_URL"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "secret_key": os.getenv("SECRET_KEY"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }
    
    # Validate required configuration
    assert config["database_url"] is not None
    assert config["secret_key"] is not None
    assert len(config["secret_key"]) >= 32  # Minimum key length
    
    # Test configuration values
    assert config["log_level"] in ["DEBUG", "INFO", "WARNING", "ERROR"]


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_async_functionality():
    """Test that async/await functionality works correctly."""
    async def sample_async_function():
        await asyncio.sleep(0.1)
        return "async_success"
    
    result = await sample_async_function()
    assert result == "async_success"


@pytest.mark.smoke
def test_json_serialization():
    """Test JSON serialization/deserialization for API responses."""
    import json
    from decimal import Decimal
    from datetime import datetime, date
    
    # Test basic JSON operations
    test_data = {
        "string": "test",
        "integer": 123,
        "float": 45.67,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"nested": "value"}
    }
    
    # Test serialization
    json_str = json.dumps(test_data)
    assert isinstance(json_str, str)
    
    # Test deserialization
    parsed_data = json.loads(json_str)
    assert parsed_data == test_data


@pytest.mark.smoke
def test_logging_functionality():
    """Test that logging is working correctly."""
    import logging
    import tempfile
    import os
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        log_file = f.name
    
    try:
        # Configure logger
        logger = logging.getLogger("smoke_test")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test logging
        logger.info("Smoke test logging check")
        logger.warning("Test warning message")
        
        # Verify log file was created and contains messages
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "Smoke test logging check" in log_content
            assert "Test warning message" in log_content
    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.unlink(log_file)


@pytest.mark.smoke
def test_critical_imports():
    """Test that all critical modules can be imported."""
    critical_modules = [
        "asyncio",
        "json",
        "datetime",
        "uuid",
        "hashlib",
        "logging",
        "os",
        "sys",
        "pathlib",
        "typing"
    ]
    
    failed_imports = []
    
    for module_name in critical_modules:
        try:
            __import__(module_name)
        except ImportError:
            failed_imports.append(module_name)
    
    assert not failed_imports, f"Failed to import critical modules: {failed_imports}"


@pytest.mark.smoke
def test_time_and_timezone():
    """Test time and timezone functionality."""
    from datetime import datetime, timezone
    import time
    
    # Test current time
    now = datetime.now()
    assert isinstance(now, datetime)
    
    # Test UTC time
    utc_now = datetime.now(timezone.utc)
    assert isinstance(utc_now, datetime)
    
    # Test timestamp conversion
    timestamp = time.time()
    dt_from_timestamp = datetime.fromtimestamp(timestamp)
    assert isinstance(dt_from_timestamp, datetime)


@pytest.mark.smoke
@pytest.mark.timeout(30)  # 30 second timeout
def test_performance_baseline():
    """Test basic performance benchmarks for smoke tests."""
    import time
    
    # Test simple computation performance
    start_time = time.time()
    
    # Simple CPU-bound task
    result = sum(i * i for i in range(10000))
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Should complete in under 1 second
    assert execution_time < 1.0, f"Performance baseline failed: {execution_time:.3f}s"
    assert result > 0  # Sanity check