#!/bin/bash

# Setup Requirements for Biometric Attendance Sync Tool
# This script installs dependencies and sets up proper permissions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAPPE_BENCH_PATH="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"
PIP_PATH="$SCRIPT_DIR/venv/bin/pip"

echo "🚀 Setting up Biometric Attendance Sync Tool..."
echo "================================================"
echo "Script directory: $SCRIPT_DIR"
echo "Frappe bench path: $FRAPPE_BENCH_PATH"
echo "Python path: $PYTHON_PATH"
echo ""

# Check if virtual environment exists
if [[ ! -f "$PYTHON_PATH" ]]; then
    echo "❌ Error: Virtual environment not found at $PYTHON_PATH"
    echo "Please ensure virtual environment is set up first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Install dependencies in virtual environment
echo "📦 Installing dependencies in virtual environment..."
cd "$SCRIPT_DIR"

if [[ -f "requirements.txt" ]]; then
    $PIP_PATH install -r requirements.txt
    if [[ $? -eq 0 ]]; then
        echo "✅ Dependencies installed successfully!"
    else
        echo "❌ Failed to install dependencies"
        exit 1
    fi
else
    echo "❌ requirements.txt not found"
    exit 1
fi

echo ""
echo "🔧 Setting up file permissions..."

# Set execute permissions for all shell scripts
chmod +x *.sh 2>/dev/null || true
chmod +x *manual*.sh 2>/dev/null || true
chmod +x manual_run_functions/*.sh 2>/dev/null || true

# Set execute permissions for Python scripts
chmod +x *.py 2>/dev/null || true
chmod +x manual_run_functions/*.py 2>/dev/null || true

# Set proper permissions for log directory
if [[ ! -d "logs" ]]; then
    mkdir -p logs
fi
chmod 755 logs

# Set proper permissions for manual_run_functions
if [[ -d "manual_run_functions" ]]; then
    chmod 755 manual_run_functions
    chmod 644 manual_run_functions/*.md 2>/dev/null || true
fi

echo "✅ File permissions set successfully!"
echo ""
echo "📋 Summary:"
echo "=========="
echo "✅ Dependencies installed in virtual environment"
echo "✅ Execute permissions set for shell scripts"
echo "✅ Execute permissions set for Python scripts" 
echo "✅ Log directory permissions configured"
echo ""
echo "🎯 Available manual scripts:"
echo "  ./start_erpnext_sync_all_manual.sh   - Start the sync service"
echo "  ./stop_erpnext_sync_all_manual.sh    - Stop the sync service (force kill)"
echo "  ./status_erpnext_sync_all_manual.sh  - Check service status"
echo ""
echo "📖 Usage:"
echo "  The service now uses manual scripts only (systemd service removed)"
echo "  Use the manual scripts above for full control and better diagnostics"
echo ""
echo "🚀 Setup completed successfully!"