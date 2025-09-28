#!/bin/bash
# Odin Build Wrapper

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
    echo -e "${PURPLE}🏗️  Odin Build 🏗️${NC}"
    echo "==============="
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --region R        - AWS region (default: eu-north-1)"
    echo "  --config C        - Configuration file (default: odin.yaml)"
    echo "  --stack-name S    - CloudFormation stack name"
    echo ""
    echo "Examples:"
    echo "  $0                              # Build with default settings"
    echo "  $0 --region us-east-1           # Build in specific region"
    echo "  $0 --config custom.yaml         # Use custom config"
    echo "  $0 --stack-name my-stack        # Use custom stack name"
    echo ""
}

# Check if help is requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

# Run Odin build
echo -e "${PURPLE}🏗️  Odin Build 🏗️${NC}"
echo "==============="
echo ""

python "$SCRIPT_DIR/odin_build.py" "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Build completed successfully${NC}"
else
    echo -e "\n${RED}❌ Build failed${NC}"
    exit 1
fi
