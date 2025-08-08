#!/bin/bash
# Comprehensive Test Suite Runner for Qenergyz
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="reports/run_${TIMESTAMP}"
PARALLEL_JOBS=${PARALLEL_JOBS:-4}
TEST_TIMEOUT=${TEST_TIMEOUT:-300}

# Create report directory
mkdir -p "$REPORT_DIR"

# Function to print status messages
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to run test category with timeout and reporting
run_test_category() {
    local category=$1
    local description=$2
    local test_command=$3
    local report_file="${REPORT_DIR}/${category}.xml"
    
    print_header "Running $description"
    
    if [[ -d "$category" ]]; then
        echo "Executing: $test_command"
        
        # Run with timeout and capture results
        if timeout $TEST_TIMEOUT bash -c "$test_command --junitxml=$report_file" 2>&1 | tee "${REPORT_DIR}/${category}.log"; then
            print_status "$description completed successfully"
            return 0
        else
            print_error "$description failed or timed out"
            return 1
        fi
    else
        print_warning "$description directory not found. Skipping..."
        return 0
    fi
}

# Start test execution
print_header "Qenergyz Comprehensive Test Suite"
echo "Started at: $(date)"
echo "Report directory: $REPORT_DIR"
echo "Parallel jobs: $PARALLEL_JOBS"
echo "Test timeout: ${TEST_TIMEOUT}s"

# Initialize counters
TOTAL_CATEGORIES=0
PASSED_CATEGORIES=0
FAILED_CATEGORIES=0

# Test execution plan (in optimal order)
declare -A TEST_PLAN=(
    ["4_infrastructure"]="Infrastructure Testing:pytest 4_infrastructure/ -v --tb=short"
    ["1_smoke"]="Smoke Testing:pytest 1_smoke/ -v --tb=short -m smoke"
    ["2_functional"]="Functional Testing:pytest 2_functional/ -v --tb=short -m functional"
    ["14_api_contract"]="API Contract Testing:pytest 14_api_contract/ -v --tb=short"
    ["3_integration"]="Integration Testing:pytest 3_integration/ -v --tb=short -m integration"
    ["5_e2e"]="End-to-End Testing:pytest 5_e2e/ -v --tb=short -m e2e"
    ["10_security"]="Security Testing:./10_security/run_security_tests.sh"
    ["8_load"]="Load Testing:./8_load/run_load_tests.sh"
    ["9_stress"]="Stress Testing:./9_stress/run_stress_tests.sh"
    ["13_reliability"]="Chaos/Reliability Testing:./13_reliability/run_chaos_tests.sh"
    ["7_regression"]="Regression Testing:pytest 7_regression/ -v --tb=short -m regression"
    ["6_network"]="Network Testing:./6_network/run_network_tests.sh"
    ["11_ui_ux"]="UI/UX Testing:./11_ui_ux/run_ui_tests.sh"
    ["12_fuzz"]="Fuzz Testing:./12_fuzz/run_fuzz_tests.sh"
    ["15_data_migration"]="Data Migration Testing:pytest 15_data_migration/ -v --tb=short"
    ["16_compatibility"]="Compatibility Testing:pytest 16_compatibility/ -v --tb=short"
    ["17_backup_restore"]="Backup/Restore Testing:pytest 17_backup_restore/ -v --tb=short"
    ["18_monitoring"]="Monitoring/Alerting Testing:pytest 18_monitoring/ -v --tb=short"
)

# Parse command line arguments
RUN_SPECIFIC=""
RUN_FAST=false
SKIP_SLOW=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --category)
            RUN_SPECIFIC="$2"
            shift 2
            ;;
        --fast)
            RUN_FAST=true
            SKIP_SLOW=true
            shift
            ;;
        --skip-slow)
            SKIP_SLOW=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --category CATEGORY    Run specific test category only"
            echo "  --fast                 Run fast tests only (skip slow categories)"
            echo "  --skip-slow           Skip slow-running tests"
            echo "  --help                Show this help message"
            echo ""
            echo "Available categories:"
            for category in $(echo "${!TEST_PLAN[@]}" | tr ' ' '\n' | sort); do
                echo "  $category"
            done
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run specific category if requested
if [[ -n "$RUN_SPECIFIC" ]]; then
    if [[ -n "${TEST_PLAN[$RUN_SPECIFIC]}" ]]; then
        IFS=':' read -r description command <<< "${TEST_PLAN[$RUN_SPECIFIC]}"
        run_test_category "$RUN_SPECIFIC" "$description" "$command"
        exit $?
    else
        print_error "Category '$RUN_SPECIFIC' not found"
        exit 1
    fi
fi

# Determine which categories to skip for fast runs
SLOW_CATEGORIES=("8_load" "9_stress" "13_reliability" "5_e2e" "11_ui_ux" "12_fuzz")

# Execute all test categories
for category in $(echo "${!TEST_PLAN[@]}" | tr ' ' '\n' | sort); do
    TOTAL_CATEGORIES=$((TOTAL_CATEGORIES + 1))
    
    # Skip slow categories if requested
    if [[ "$SKIP_SLOW" == true ]] && [[ " ${SLOW_CATEGORIES[@]} " =~ " ${category} " ]]; then
        print_warning "Skipping slow category: $category"
        continue
    fi
    
    IFS=':' read -r description command <<< "${TEST_PLAN[$category]}"
    
    if run_test_category "$category" "$description" "$command"; then
        PASSED_CATEGORIES=$((PASSED_CATEGORIES + 1))
    else
        FAILED_CATEGORIES=$((FAILED_CATEGORIES + 1))
    fi
done

# Generate summary report
print_header "Test Execution Summary"
echo "Completed at: $(date)"
echo "Total categories: $TOTAL_CATEGORIES"
echo "Passed categories: $PASSED_CATEGORIES"
echo "Failed categories: $FAILED_CATEGORIES"

if [[ $FAILED_CATEGORIES -eq 0 ]]; then
    print_status "All test categories passed! 🎉"
    EXIT_CODE=0
else
    print_error "$FAILED_CATEGORIES test categories failed"
    EXIT_CODE=1
fi

# Generate consolidated report
python3 scripts/generate_reports.py "$REPORT_DIR"

echo ""
echo "📊 Detailed reports available in: $REPORT_DIR"
echo "📈 HTML report: $REPORT_DIR/consolidated_report.html"

exit $EXIT_CODE