#!/bin/bash
# Odin Test Runner

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
    echo -e "${PURPLE}⚡ Odin Test Runner ⚡${NC}"
    echo "======================"
    echo ""
    echo "Usage: $0 [test_type]"
    echo ""
    echo "Test Types:"
    echo "  infrastructure  - Test Odin infrastructure management"
    echo "  pipeline        - Test Odin pipeline execution"
    echo "  all             - Run all tests"
    echo ""
    echo "Examples:"
    echo "  $0 infrastructure    # Test infrastructure only"
    echo "  $0 pipeline         # Test pipeline only"
    echo "  $0 all              # Run all tests"
    echo ""
}

# Check if test type is provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

TEST_TYPE=$1

echo -e "${PURPLE}⚡ Running Odin Tests ⚡${NC}"
echo "======================"
echo ""

case $TEST_TYPE in
    "infrastructure")
        echo -e "${BLUE}🧪 Running Infrastructure Tests${NC}"
        python "$SCRIPT_DIR/test_odin_infrastructure.py"
        ;;
    "pipeline")
        echo -e "${BLUE}🧪 Running Pipeline Tests${NC}"
        python "$SCRIPT_DIR/test_odin_pipeline.py"
        ;;
    "all")
        echo -e "${BLUE}🧪 Running All Tests${NC}"
        echo ""
        echo "1. Infrastructure Tests:"
        python "$SCRIPT_DIR/test_odin_infrastructure.py"
        echo ""
        echo "2. Pipeline Tests:"
        python "$SCRIPT_DIR/test_odin_pipeline.py"
        ;;
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        show_usage
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Odin tests completed successfully${NC}"
else
    echo -e "\n${RED}❌ Odin tests failed${NC}"
    exit 1
fi
