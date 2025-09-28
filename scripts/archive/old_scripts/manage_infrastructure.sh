#!/bin/bash
# AWS Batch Infrastructure Management Wrapper

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment
source "$PROJECT_DIR/.venv/bin/activate"

# Function to show usage
show_usage() {
    echo -e "${BLUE}🦌 AWS Batch Infrastructure Manager${NC}"
    echo "=========================================="
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup       - Setup infrastructure if it doesn't exist"
    echo "  status      - Show infrastructure status"
    echo "  scale-up    - Scale up compute environment (default: 4 vCPUs)"
    echo "  scale-down  - Scale down compute environment to 0"
    echo "  jobs        - List active batch jobs"
    echo "  cleanup     - Delete infrastructure (WARNING: usually not needed)"
    echo ""
    echo "Options:"
    echo "  --vcpus N   - Number of vCPUs for scale-up (default: 4)"
    echo "  --region R  - AWS region (default: eu-north-1)"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Setup infrastructure"
    echo "  $0 status                  # Check status"
    echo "  $0 scale-up --vcpus 8      # Scale up to 8 vCPUs"
    echo "  $0 scale-down              # Scale down to 0"
    echo "  $0 jobs                    # List active jobs"
    echo ""
}

# Check if command is provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# Run the infrastructure manager
echo -e "${BLUE}🚀 Running Infrastructure Manager${NC}"
echo "=================================="
echo ""

python "$SCRIPT_DIR/infrastructure_manager.py" "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Operation completed successfully${NC}"
else
    echo -e "\n${RED}❌ Operation failed${NC}"
    exit 1
fi
