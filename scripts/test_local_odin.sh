#!/bin/bash
"""
Test Local Odin Setup

Test the local Odin infrastructure and pipeline.
"""

set -e

echo "🧪 Testing Local Odin Setup"
echo "============================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Add src to Python path
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

cd "$PROJECT_ROOT"

echo "1️⃣ Starting Local Infrastructure"
echo "================================"
echo ""

# Start local infrastructure
echo "🐳 Starting Docker services..."
docker-compose -f docker-compose.local.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 30

echo "2️⃣ Testing Odin CLI"
echo "==================="
echo ""

# Test Odin CLI with local config
echo "📋 Testing Odin status..."
python -m odin.cli --config odin.local.yaml infrastructure status

echo "📊 Testing Odin pipeline status..."
python -m odin.cli --config odin.local.yaml pipeline status

echo "3️⃣ Testing Local Pipeline"
echo "=========================="
echo ""

# Test local pipeline
echo "🚀 Running local pipeline..."
python -m odin.cli --config odin.local.yaml pipeline run

echo "4️⃣ Testing Data Management"
echo "============================"
echo ""

# Test data management
echo "📤 Testing data upload..."
python -m odin.cli --config odin.local.yaml data upload

echo "📋 Testing data listing..."
python -m odin.cli --config odin.local.yaml data list

echo "5️⃣ Testing Cost Management"
echo "=========================="
echo ""

# Test cost management
echo "💰 Testing cost report..."
python -m odin.cli --config odin.local.yaml cost report

echo "6️⃣ Testing Infrastructure Management"
echo "===================================="
echo ""

# Test infrastructure management
echo "📈 Testing scale up..."
python -m odin.cli --config odin.local.yaml infrastructure scale-up

echo "📉 Testing scale down..."
python -m odin.cli --config odin.local.yaml infrastructure scale-down

echo "7️⃣ Testing Teardown"
echo "===================="
echo ""

# Test teardown
echo "🗑️ Testing teardown..."
python -m odin.cli --config odin.local.yaml infrastructure teardown

echo "🎉 Local Odin Test Complete!"
echo "============================"
echo "✅ All tests passed!"
echo ""
echo "📊 Test Summary:"
echo "  - Local infrastructure setup ✅"
echo "  - Odin CLI functionality ✅"
echo "  - Local pipeline execution ✅"
echo "  - Data management ✅"
echo "  - Cost management ✅"
echo "  - Infrastructure management ✅"
echo "  - Teardown ✅"
