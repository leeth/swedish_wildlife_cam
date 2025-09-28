#!/bin/bash
# Test Runner for Odin

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment
source "$PROJECT_DIR/.venv/bin/activate"

# Function to show usage
show_usage() {
    echo -e "${PURPLE}🧪 Odin Test Runner 🧪${NC}"
    echo "======================"
    echo ""
    echo "Usage: $0 [test_type]"
    echo ""
    echo "Test Types:"
    echo "  unit         - Run unit tests only"
    echo "  integration  - Run integration tests only"
    echo "  all          - Run all tests"
    echo "  coverage     - Run tests with coverage"
    echo ""
    echo "Examples:"
    echo "  $0 unit           # Run unit tests only"
    echo "  $0 integration    # Run integration tests only"
    echo "  $0 all            # Run all tests"
    echo "  $0 coverage       # Run tests with coverage report"
    echo ""
}

# Check if test type is provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

TEST_TYPE=$1

echo -e "${PURPLE}🧪 Running Odin Tests 🧪${NC}"
echo "======================"
echo ""

case $TEST_TYPE in
    "unit")
        echo -e "${BLUE}🔬 Running Unit Tests${NC}"
        python -m pytest tests/test_odin.py -v
        ;;
    "integration")
        echo -e "${BLUE}🔗 Running Integration Tests${NC}"
        python tests/test_odin.py
        ;;
    "all")
        echo -e "${BLUE}🧪 Running All Tests${NC}"
        echo ""
        echo "1. Unit Tests:"
        python -m pytest tests/test_odin.py -v
        echo ""
        echo "2. Integration Tests:"
        python tests/test_odin.py
        ;;
    "coverage")
        echo -e "${BLUE}📊 Running Tests with Coverage${NC}"
        python -m pytest tests/test_odin.py --cov=scripts.odin --cov-report=html --cov-report=term
        echo ""
        echo "📊 Coverage report generated in htmlcov/"
        ;;
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        show_usage
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${RED}❌ Some tests failed${NC}"
    exit 1
fi
