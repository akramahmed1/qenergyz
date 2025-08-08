# Smoke Testing

Smoke tests are the most basic level of testing that ensure the core functionality of the Qenergyz platform is working. These tests are designed to be fast, reliable, and catch critical failures early.

## Overview

Smoke tests validate:
- ✅ Application startup and shutdown
- ✅ Database connectivity
- ✅ API health endpoints
- ✅ Core service availability
- ✅ Configuration loading
- ✅ Critical dependencies

## Test Files

- `test_smoke_basic.py` - Basic application startup and configuration tests
- `test_api_health.py` - API health check and readiness tests
- `smoke_test_config.yml` - Smoke test configuration

## Running Smoke Tests

### Quick Run (Recommended)
```bash
# From the tests directory
pytest 1_smoke/ -v -m smoke

# Run with specific markers
pytest 1_smoke/ -v -m "smoke and not slow"

# Generate report
pytest 1_smoke/ -v --html=reports/smoke_report.html
```

### CI/CD Integration
```bash
# Fast smoke test for CI
pytest 1_smoke/ -v -m smoke --tb=short --maxfail=3
```

## Test Configuration

### Environment Variables
```bash
# Required for smoke tests
export TESTING=true
export LOG_LEVEL=INFO
export API_BASE_URL=http://localhost:8000
```

### Smoke Test Config (`smoke_test_config.yml`)
```yaml
timeouts:
  startup: 30
  api_response: 5
  health_check: 10

endpoints:
  health: /health
  ready: /ready
  metrics: /metrics

critical_services:
  - database
  - redis
  - trading_service
  - risk_service
```

## Success Criteria

Smoke tests must:
- ✅ Complete in under 60 seconds
- ✅ Have 100% pass rate for critical functionality
- ✅ Detect application startup failures
- ✅ Validate core API endpoints
- ✅ Check database connectivity

## Extending Smoke Tests

To add new smoke tests:

1. Create test functions with `@pytest.mark.smoke` decorator
2. Keep tests simple and fast (< 5 seconds each)
3. Focus on critical path validation
4. Use appropriate timeouts
5. Mock external dependencies

Example:
```python
@pytest.mark.smoke
def test_new_critical_service():
    """Test new critical service startup"""
    # Your test implementation
    assert service.is_healthy()
```