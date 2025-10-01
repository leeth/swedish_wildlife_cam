#!/bin/bash

# Start Wildlife Pipeline without Docker daemon
echo "🚀 Starting Wildlife Pipeline (No Docker Mode)..."

# Check if we're in a development environment
echo "🔍 Checking development environment..."

# Check Python environment
if python3 --version > /dev/null 2>&1; then
    echo "✅ Python $(python3 --version) available"
else
    echo "❌ Python not found"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ] || [ -d ".venv" ]; then
    echo "✅ Virtual environment found"
    if [ -d "venv" ]; then
        echo "🔄 Activating venv..."
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        echo "🔄 Activating .venv..."
        source .venv/bin/activate
    fi
else
    echo "⚠️ No virtual environment found, using system Python"
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
if ! python3 -c "import ultralytics" 2>/dev/null; then
    echo "🔄 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the pipeline in development mode
echo "🏃 Starting Wildlife Pipeline in development mode..."
echo ""
echo "Available commands:"
echo "  python3 -m src.odin.cli --help"
echo "  python3 -m src.odin.cli infrastructure status"
echo "  python3 -m src.odin.cli pipeline run"
echo ""
echo "🌐 For full Docker services, please:"
echo "  1. Start Docker Desktop"
echo "  2. Run: make fix-docker"
echo "  3. Run: docker-compose -f conf/docker/docker-compose.local.yml up -d"
echo ""
echo "✅ Wildlife Pipeline ready for development!"
