#!/bin/bash

# Simple ERPNext to Device Sync
# Auto-detects sync mode based on last_sync

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"
SCRIPT_PATH="$SCRIPT_DIR/sync_from_erpnext_to_device.py"
LOG_FILE="$SCRIPT_DIR/logs/sync_from_erpnext_to_device/sync_to_device.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check help
if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$1" = "help" ]; then
    echo "ERPNext to Device Sync - Auto Mode"
    echo ""
    echo "Usage: $0"
    echo ""
    echo "Auto-detects sync mode:"
    echo "  - First run: Sync all employees"
    echo "  - Subsequent runs: Sync only fingerprint changes since last_sync"
    echo ""
    echo "Log file: $LOG_FILE"
    exit 0
fi

# Check if Python exists
if [ ! -f "$PYTHON_PATH" ]; then
    print_error "Python not found: $PYTHON_PATH"
    exit 1
fi

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    print_error "Sync script not found: $SCRIPT_PATH"
    exit 1
fi

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs/sync_from_erpnext_to_device"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

print_info "Starting ERPNext to Device Sync (Auto Mode)"
print_info "Log file: $LOG_FILE"

# Execute sync
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting auto sync" >> "$LOG_FILE"

$PYTHON_PATH "$SCRIPT_PATH" 2>&1

RESULT=$?

# Log completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Auto sync completed with exit code: $RESULT" >> "$LOG_FILE"

if [ $RESULT -eq 0 ]; then
    print_success "Sync completed successfully!"
else
    print_error "Sync failed!"
    # Show last few lines of error log
    echo ""
    print_info "Last 5 lines of log:"
    tail -n 5 "$LOG_FILE" 2>/dev/null || echo "Could not read log file"
fi

print_info "Check full log: $LOG_FILE"

exit $RESULT