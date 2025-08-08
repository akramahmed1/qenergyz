# Qenergyz Comprehensive Testing Suite

This directory contains a comprehensive testing suite covering all critical testing types for the Qenergyz energy trading platform.

## Directory Structure

```
tests/
├── README.md                           # This file - Testing documentation
├── conftest.py                        # Shared pytest fixtures
├── requirements.txt                   # Testing dependencies
├── scripts/                           # Testing automation scripts
│   ├── run_all_tests.sh              # Execute all test types
│   ├── setup_test_env.sh             # Set up testing environment
│   └── generate_reports.py           # Generate consolidated test reports
├── 1_smoke/                          # Smoke Testing
│   ├── README.md                     # Smoke testing documentation
│   ├── test_smoke_basic.py          # Basic service startup tests
│   ├── test_api_health.py           # API health check tests
│   └── smoke_test_config.yml        # Smoke test configuration
├── 2_functional/                     # Functional Testing
│   ├── README.md                     # Functional testing documentation
│   ├── backend/                      # Backend functional tests
│   ├── frontend/                     # Frontend functional tests
│   └── api/                         # API functional tests
├── 3_integration/                    # Integration Testing
│   ├── README.md                     # Integration testing documentation
│   ├── service_to_service/          # Service-to-service tests
│   ├── api_integration/             # API integration tests
│   └── third_party/                 # 3rd party integration tests
├── 4_infrastructure/                 # Technical/Infrastructure Testing
│   ├── README.md                     # Infrastructure testing documentation
│   ├── docker/                      # Container testing
│   ├── network/                     # Network configuration testing
│   └── iac/                        # Infrastructure as Code testing
├── 5_e2e/                           # End-to-End Testing
│   ├── README.md                     # E2E testing documentation
│   ├── playwright/                  # Playwright E2E tests
│   ├── cypress/                     # Cypress E2E tests (alternative)
│   └── user_workflows/              # Complete user workflow tests
├── 6_network/                       # Network Testing
│   ├── README.md                     # Network testing documentation
│   ├── connectivity/                # Connection tests
│   ├── latency/                     # Latency tests
│   └── failure_simulation/          # Network failure tests
├── 7_regression/                    # Regression Testing
│   ├── README.md                     # Regression testing documentation
│   ├── automated_suite/             # Automated regression tests
│   └── baseline/                    # Baseline test results
├── 8_load/                         # Load Testing
│   ├── README.md                     # Load testing documentation
│   ├── locust/                      # Locust load tests
│   ├── k6/                         # k6 load tests
│   └── jmeter/                     # JMeter load tests
├── 9_stress/                       # Stress Testing
│   ├── README.md                     # Stress testing documentation
│   ├── system_limits/              # System limit tests
│   └── auto_scaling/               # Auto-scaling validation
├── 10_security/                    # Security Testing
│   ├── README.md                     # Security testing documentation
│   ├── sast/                       # Static Application Security Testing
│   ├── dast/                       # Dynamic Application Security Testing
│   ├── dependency_scan/            # Dependency vulnerability scanning
│   ├── secret_detection/           # Secret detection tests
│   └── penetration/                # Penetration testing
├── 11_ui_ux/                      # UI/UX Testing
│   ├── README.md                     # UI/UX testing documentation
│   ├── visual_regression/          # Visual regression tests
│   ├── accessibility/              # Accessibility tests
│   └── cross_browser/              # Cross-browser compatibility tests
├── 12_fuzz/                        # Fuzz Testing
│   ├── README.md                     # Fuzz testing documentation
│   ├── api_fuzzing/                # API fuzzing tests
│   └── input_fuzzing/              # User input fuzzing tests
├── 13_reliability/                 # Reliability/Chaos Testing
│   ├── README.md                     # Reliability testing documentation
│   ├── chaos_monkey/               # Chaos engineering tests
│   ├── fault_injection/            # Fault injection tests
│   └── self_healing/               # Self-healing validation
├── 14_api_contract/                # API Contract Testing
│   ├── README.md                     # API contract testing documentation
│   ├── openapi/                    # OpenAPI/Swagger contract tests
│   └── pact/                      # Consumer-driven contract tests
├── 15_data_migration/              # Data Migration Testing
│   ├── README.md                     # Data migration testing documentation
│   ├── migration_tests/            # Migration validation tests
│   └── rollback_tests/             # Rollback validation tests
├── 16_compatibility/               # Upgrade/Compatibility Testing
│   ├── README.md                     # Compatibility testing documentation
│   ├── backward_compatibility/     # Backward compatibility tests
│   └── upgrade_downgrade/          # Upgrade/downgrade tests
├── 17_backup_restore/              # Backup/Restore Testing
│   ├── README.md                     # Backup/restore testing documentation
│   ├── backup_tests/               # Backup validation tests
│   └── restore_tests/              # Restore validation tests
└── 18_monitoring/                  # Monitoring/Alerting Testing
    ├── README.md                     # Monitoring testing documentation
    ├── metrics/                    # Metrics validation tests
    └── alerting/                   # Alerting validation tests
```

## Quick Start

1. **Set up the testing environment:**
   ```bash
   cd tests
   ./scripts/setup_test_env.sh
   ```

2. **Install testing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run all tests:**
   ```bash
   ./scripts/run_all_tests.sh
   ```

4. **Run specific test categories:**
   ```bash
   # Smoke tests
   pytest 1_smoke/ -v
   
   # Load tests
   cd 8_load/locust && locust -f locustfile.py
   
   # Security tests
   cd 10_security && ./run_security_tests.sh
   ```

## Test Execution Order

The tests are designed to run in the following order for optimal results:

1. **Infrastructure Tests** (4_infrastructure) - Ensure environment is ready
2. **Smoke Tests** (1_smoke) - Basic health checks
3. **Functional Tests** (2_functional) - Core functionality validation
4. **Integration Tests** (3_integration) - Service integration validation
5. **API Contract Tests** (14_api_contract) - API contract validation
6. **End-to-End Tests** (5_e2e) - Complete user workflows
7. **Security Tests** (10_security) - Security validation
8. **Performance Tests** (8_load, 9_stress) - Performance validation
9. **Reliability Tests** (13_reliability) - Chaos and fault testing
10. **Regression Tests** (7_regression) - Regression validation
11. **Specialized Tests** (6_network, 11_ui_ux, 12_fuzz) - Specialized validation

## Configuration

Each test category has its own configuration files and can be run independently or as part of the comprehensive suite. See individual README files in each directory for specific configuration options.

## Reporting

Test results are aggregated and reported using:
- **Pytest HTML reports** for functional tests
- **Allure reports** for comprehensive test reporting
- **Custom dashboards** for performance and security metrics
- **CI/CD integration** with GitHub Actions

## Contributing

When adding new tests:
1. Follow the established directory structure
2. Include comprehensive documentation
3. Add appropriate test markers
4. Update this README with any new test categories
5. Ensure tests can run in isolation and as part of the suite

For more details, see the individual README files in each test category directory.