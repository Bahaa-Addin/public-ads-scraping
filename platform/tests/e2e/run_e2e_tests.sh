#!/bin/bash

# E2E Test Runner Script
# 
# This script runs the complete E2E test suite including:
# - pytest-bdd API tests
# - Playwright frontend tests
# 
# Usage:
#   ./run_e2e_tests.sh           # Run all tests
#   ./run_e2e_tests.sh api       # Run only API tests
#   ./run_e2e_tests.sh frontend  # Run only frontend tests
#   ./run_e2e_tests.sh critical  # Run only critical tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
DASHBOARD_BACKEND_URL="${DASHBOARD_BACKEND_URL:-http://localhost:8000}"
AGENT_API_URL="${AGENT_API_URL:-http://localhost:8081}"
SCRAPER_API_URL="${SCRAPER_API_URL:-http://localhost:3001}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

# Report directories
REPORTS_DIR="$SCRIPT_DIR/reports"
mkdir -p "$REPORTS_DIR"

# Functions
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_service() {
    local url=$1
    local name=$2
    
    if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
        print_success "$name is running at $url"
        return 0
    else
        print_warning "$name is not responding at $url"
        return 1
    fi
}

check_services() {
    print_header "Checking Services"
    
    local all_running=true
    
    check_service "$DASHBOARD_BACKEND_URL/api/v1/health" "Dashboard Backend" || all_running=false
    check_service "$AGENT_API_URL/health" "Agent API" || all_running=false
    check_service "$SCRAPER_API_URL/health" "Scraper Service" || all_running=false
    check_service "$FRONTEND_URL" "Frontend" || all_running=false
    
    if [ "$all_running" = false ]; then
        print_warning "Some services are not running. Tests may fail."
        echo ""
        echo "To start services, run:"
        echo "  Dashboard Backend: cd dashboard/backend && uvicorn app.main:app --port 8000"
        echo "  Agent API:         cd agent && uvicorn api:app --port 8081"
        echo "  Scraper:           cd scrapers && node server.js"
        echo "  Frontend:          cd dashboard/frontend && npm run dev"
        echo ""
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

run_api_tests() {
    print_header "Running API Tests (pytest-bdd)"
    
    cd "$SCRIPT_DIR"
    
    # Check if virtual environment exists
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        print_warning "Virtual environment not found. Creating..."
        python3 -m venv "$PROJECT_ROOT/venv"
    fi
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv/bin/activate"
    
    # Install test dependencies
    pip install -q -r requirements-test.txt
    
    # Run pytest-bdd tests
    local pytest_args="-v --tb=short"
    
    if [ "$1" = "critical" ]; then
        pytest_args="$pytest_args -m critical"
    fi
    
    pytest steps/ $pytest_args \
        --html="$REPORTS_DIR/api-test-report.html" \
        --self-contained-html \
        2>&1 | tee "$REPORTS_DIR/api-test-output.log"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        print_success "API tests passed"
    else
        print_error "API tests failed with exit code $exit_code"
    fi
    
    return $exit_code
}

run_frontend_tests() {
    print_header "Running Frontend Tests (Playwright)"
    
    cd "$SCRIPT_DIR/playwright"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "Installing Playwright dependencies..."
        npm install
        npx playwright install chromium
    fi
    
    # Run Playwright tests
    local playwright_args=""
    
    if [ "$1" = "critical" ]; then
        playwright_args="--grep @critical"
    fi
    
    FRONTEND_URL="$FRONTEND_URL" npx playwright test $playwright_args \
        2>&1 | tee "$REPORTS_DIR/frontend-test-output.log"
    
    local exit_code=${PIPESTATUS[0]}
    
    # Move report to reports directory
    if [ -d "playwright-report" ]; then
        mv playwright-report "$REPORTS_DIR/playwright-report"
    fi
    
    if [ $exit_code -eq 0 ]; then
        print_success "Frontend tests passed"
    else
        print_error "Frontend tests failed with exit code $exit_code"
    fi
    
    return $exit_code
}

generate_summary() {
    print_header "Test Summary"
    
    echo "Reports generated in: $REPORTS_DIR"
    echo ""
    
    if [ -f "$REPORTS_DIR/api-test-report.html" ]; then
        echo "  - API Test Report: $REPORTS_DIR/api-test-report.html"
    fi
    
    if [ -d "$REPORTS_DIR/playwright-report" ]; then
        echo "  - Playwright Report: $REPORTS_DIR/playwright-report/index.html"
    fi
    
    echo ""
    echo "To view Playwright report:"
    echo "  cd $SCRIPT_DIR/playwright && npx playwright show-report $REPORTS_DIR/playwright-report"
}

# Main execution
main() {
    print_header "E2E Test Suite"
    
    local mode="${1:-all}"
    local test_filter="${2:-}"
    
    case $mode in
        api)
            check_services
            run_api_tests "$test_filter"
            ;;
        frontend)
            check_services
            run_frontend_tests "$test_filter"
            ;;
        critical)
            check_services
            run_api_tests "critical"
            run_frontend_tests "critical"
            ;;
        all)
            check_services
            
            local api_result=0
            local frontend_result=0
            
            run_api_tests "$test_filter" || api_result=$?
            run_frontend_tests "$test_filter" || frontend_result=$?
            
            generate_summary
            
            if [ $api_result -ne 0 ] || [ $frontend_result -ne 0 ]; then
                print_error "Some tests failed"
                exit 1
            else
                print_success "All tests passed"
            fi
            ;;
        *)
            echo "Usage: $0 [all|api|frontend|critical] [test_filter]"
            echo ""
            echo "Commands:"
            echo "  all       Run all tests (default)"
            echo "  api       Run only API tests (pytest-bdd)"
            echo "  frontend  Run only frontend tests (Playwright)"
            echo "  critical  Run only critical tests"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 api                # Run API tests only"
            echo "  $0 frontend           # Run frontend tests only"
            echo "  $0 api jobs           # Run API tests for jobs feature"
            exit 0
            ;;
    esac
}

main "$@"
