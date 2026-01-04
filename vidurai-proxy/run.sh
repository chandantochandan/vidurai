#!/bin/bash
# Vidurai Proxy Server - Startup Script

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Check .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Copy .env.example to .env and configure API keys"
    echo ""
fi

# Start server
echo "Starting Vidurai Proxy Server..."
python3 src/main.py
