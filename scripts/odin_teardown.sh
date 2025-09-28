#!/bin/bash
# Odin Teardown Wrapper

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
    echo -e "${PURPLE}🗑️  Odin Teardown 🗑️${NC}"
    echo "=================="
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --list-only     - Only list resources, do not teardown"
    echo "  --include-s3    - Include S3 bucket teardown"
    echo "  --force        - Force teardown without confirmation"
    echo "  --region R      - AWS region (default: eu-north-1)"
    echo ""
    echo "Examples:"
    echo "  $0 --list-only              # List all wildlife resources"
    echo "  $0 --include-s3             # Teardown including S3 buckets"
    echo "  $0 --force                  # Force teardown without confirmation"
    echo "  $0 --region us-east-1       # Teardown in specific region"
    echo ""
}

# Check if help is requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

# Run Odin teardown
echo -e "${PURPLE}🗑️  Odin Teardown 🗑️${NC}"
echo "=================="
echo ""

python "$SCRIPT_DIR/odin_teardown.py" "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Teardown completed successfully${NC}"
else
    echo -e "\n${RED}❌ Teardown failed${NC}"
    exit 1
fi
