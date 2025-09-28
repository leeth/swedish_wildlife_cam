#!/bin/bash
# Odin - The All-Knowing Father
# Wrapper script for Odin commands

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

# Function to show Odin's wisdom
show_odin_wisdom() {
    echo -e "${PURPLE}⚡ Odin - The All-Knowing Father ⚡${NC}"
    echo "=========================================="
    echo ""
    echo "Odin manages the entire wildlife processing world:"
    echo "• Sets up infrastructure as needed"
    echo "• Runs Munin/Hugin pipelines"
    echo "• Handles cost optimization"
    echo "• Cleans up when done"
    echo ""
    echo "Commands:"
    echo "  setup     - Setup complete infrastructure"
    echo "  run       - Run complete pipeline with all data"
    echo "  status    - Show infrastructure and pipeline status"
    echo "  cleanup   - Clean up all resources (use with caution)"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Setup infrastructure"
    echo "  $0 run                      # Run complete pipeline"
    echo "  $0 run --stages stage1 stage2  # Run specific stages"
    echo "  $0 status                  # Check status"
    echo "  $0 cleanup                  # Clean up everything"
    echo ""
}

# Check if command is provided
if [ $# -eq 0 ]; then
    show_odin_wisdom
    exit 1
fi

# Run Odin
echo -e "${PURPLE}⚡ Odin Awakens ⚡${NC}"
echo "=================="
echo ""

python "$SCRIPT_DIR/odin.py" "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Odin's wisdom prevails${NC}"
else
    echo -e "\n${RED}❌ Odin's power failed${NC}"
    exit 1
fi
