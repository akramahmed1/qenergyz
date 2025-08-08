# Security Testing Suite

Comprehensive security testing to identify vulnerabilities and ensure the Qenergyz platform meets security standards.

## Overview

This directory contains security testing tools and scenarios covering:
- **SAST** (Static Application Security Testing)
- **DAST** (Dynamic Application Security Testing) 
- **Dependency Scanning** for known vulnerabilities
- **Secret Detection** in code and configs
- **Penetration Testing** for common vulnerabilities

## Directory Structure

```
10_security/
├── sast/                    # Static analysis security testing
│   ├── bandit_config.yml   # Bandit configuration
│   ├── semgrep_rules.yml   # Custom Semgrep rules
│   └── run_sast.sh         # SAST execution script
├── dast/                    # Dynamic analysis security testing
│   ├── zap_baseline.py     # OWASP ZAP baseline scan
│   ├── api_security_tests.py # API security tests
│   └── run_dast.sh         # DAST execution script
├── dependency_scan/         # Dependency vulnerability scanning
│   ├── safety_check.py     # Python dependency scanning
│   ├── npm_audit.sh        # Node.js dependency scanning
│   └── requirements_scan.py # Requirements analysis
├── secret_detection/        # Secret and credential detection
│   ├── truffleHog_scan.py  # Git history secret scanning
│   ├── detect_secrets.py   # Code secret detection
│   └── config_scan.py      # Configuration file scanning
└── penetration/             # Penetration testing
    ├── sql_injection.py    # SQL injection tests
    ├── xss_tests.py        # Cross-site scripting tests
    ├── csrf_tests.py       # CSRF protection tests
    └── auth_bypass.py      # Authentication bypass tests
```

## Quick Start

### Run All Security Tests
```bash
cd 10_security
./run_security_tests.sh
```

### Run Individual Test Categories
```bash
# Static analysis
./sast/run_sast.sh

# Dynamic analysis  
./dast/run_dast.sh

# Dependency scanning
python dependency_scan/safety_check.py

# Secret detection
python secret_detection/detect_secrets.py
```

## Security Test Categories

### 1. Static Application Security Testing (SAST)
- **Bandit**: Python security linter
- **Semgrep**: Custom security rules
- **Code quality**: Security-focused code analysis

### 2. Dynamic Application Security Testing (DAST)  
- **OWASP ZAP**: Automated vulnerability scanning
- **API Security**: REST API vulnerability testing
- **Authentication**: Auth mechanism testing

### 3. Dependency Scanning
- **Safety**: Python package vulnerability scanning
- **NPM Audit**: Node.js dependency checking
- **License Compliance**: Open source license validation

### 4. Secret Detection
- **TruffleHog**: Git history secret scanning
- **detect-secrets**: Code and config secret detection
- **API Key Detection**: Hardcoded credential identification

### 5. Penetration Testing
- **SQL Injection**: Database injection vulnerability tests
- **XSS**: Cross-site scripting vulnerability tests
- **CSRF**: Cross-site request forgery tests
- **Authentication Bypass**: Auth mechanism security tests

## Security Compliance Standards

This testing suite helps validate compliance with:
- **OWASP Top 10** - Web application security risks
- **SANS Top 25** - Most dangerous software errors  
- **NIST Cybersecurity Framework** - Security controls
- **SOC 2 Type II** - Security and availability controls
- **ISO 27001** - Information security management

## Reporting and Metrics

Security test results include:
- **Vulnerability severity** (Critical, High, Medium, Low)
- **CVSS scores** for identified vulnerabilities
- **Remediation guidance** for security issues
- **Compliance status** against security standards
- **Trend analysis** for security posture over time

## Integration with CI/CD

Security tests are integrated into the CI/CD pipeline:
- **Pre-commit hooks** for secret detection
- **Pull request checks** for SAST findings
- **Nightly builds** for comprehensive security scanning
- **Production deployment gates** based on security thresholds