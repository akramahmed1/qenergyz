# Load Testing with Locust

Load testing simulates realistic user behavior and API load to validate system performance under normal operating conditions.

## Overview

This directory contains load testing scenarios using Locust to simulate:
- Multiple concurrent users
- Realistic API request patterns
- Various trading workflows
- System performance validation

## Files

- `locustfile.py` - Main Locust configuration and user behavior
- `trading_scenarios.py` - Trading-specific load test scenarios
- `config.py` - Load testing configuration
- `run_load_tests.sh` - Script to execute load tests

## Quick Start

### Install Locust
```bash
pip install locust
```

### Run Load Tests
```bash
# Start Locust web UI
locust -f locustfile.py --host=http://localhost:8000

# Run headless load test
locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 300s

# Run with custom configuration
./run_load_tests.sh
```

## Test Scenarios

### 1. Basic API Load Test
- **Users**: 10-100 concurrent users
- **Duration**: 5 minutes
- **Endpoints**: Health, authentication, basic CRUD operations

### 2. Trading Workflow Load Test
- **Users**: 25-250 concurrent traders
- **Duration**: 10 minutes
- **Scenarios**: Login, view positions, create trades, market data

### 3. Peak Load Simulation
- **Users**: 100-1000 concurrent users
- **Duration**: 30 minutes
- **Focus**: System behavior under peak trading hours

## Performance Targets

| Metric | Target |
|--------|--------|
| Response Time (95th percentile) | < 500ms |
| Response Time (Average) | < 200ms |
| Error Rate | < 1% |
| Throughput | > 100 RPS |
| CPU Usage | < 80% |
| Memory Usage | < 2GB |

## Configuration

Environment variables for load testing:
```bash
export LOAD_TEST_TARGET_HOST=http://localhost:8000
export LOAD_TEST_USERS=50
export LOAD_TEST_SPAWN_RATE=5
export LOAD_TEST_DURATION=300
```