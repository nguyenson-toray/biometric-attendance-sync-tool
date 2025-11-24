#!/bin/bash

# Clean Data Employee Left Script
# Comprehensive cleanup for employees with status "Left"
# - Deletes fingerprint records from ERPNext
# - Clears fingerprint templates from devices (keeps user_id)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"
SCRIPT_PATH="$SCRIPT_DIR/02.clean_data_employee_left.py"
LOG_FILE="$SCRIPT_DIR/logs/clean_data_employee_left/clean_left_employees.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check help
if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$1" = "help" ]; then
    echo "Clean Data Employee Left - Cleanup tool for departed employees"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run    Show what would be cleaned without making changes"
    echo "  --help, -h   Show this help message"
    echo ""
    echo "This tool performs comprehensive cleanup for employees with status 'Left':"
    echo "  1. Date validation: Only process employees where current date > relieving_date"
    echo "  2. Delete fingerprint records from ERPNext"
    echo "  3. Clear fingerprint templates from devices (keep user_id for attendance history)"
    echo ""
    echo "Log file: $LOG_FILE"
    echo ""
    echo "Cron job example (run daily at 23:00):"
    echo "  0 23 * * * cd $SCRIPT_DIR && ./clean_data_employee_left.sh >/dev/null 2>&1"
    exit 0
fi

# Check if Python exists
if [ ! -f "$PYTHON_PATH" ]; then
    print_error "Python not found: $PYTHON_PATH"
    print_info "Please run setup first or check virtual environment"
    exit 1
fi

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    print_error "Clean script not found: $SCRIPT_PATH"
    exit 1
fi

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs/clean_data_employee_left"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

print_info "Starting Left Employee Data Cleanup"
print_info "Log file: $LOG_FILE"

# Handle dry-run
if [ "$1" = "--dry-run" ]; then
    print_warning "DRY RUN MODE - No actual changes will be made"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting dry run cleanup" >> "$LOG_FILE"
    
    $PYTHON_PATH "$SCRIPT_PATH" --dry-run 2>&1
    RESULT=$?
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Dry run completed with exit code: $RESULT" >> "$LOG_FILE"
    
    if [ $RESULT -eq 0 ]; then
        print_success "Dry run completed successfully!"
    else
        print_error "Dry run failed!"
    fi
    
    print_info "Check full log: $LOG_FILE"
    exit $RESULT
fi

# Execute actual cleanup
print_warning "LIVE MODE - This will make actual changes to ERPNext and devices"
print_info "Starting in 5 seconds... (Ctrl+C to cancel)"
sleep 5

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting left employee cleanup" >> "$LOG_FILE"

$PYTHON_PATH "$SCRIPT_PATH" 2>&1

RESULT=$?

# Log completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Left employee cleanup completed with exit code: $RESULT" >> "$LOG_FILE"

if [ $RESULT -eq 0 ]; then
    print_success "Left employee cleanup completed successfully!"
else
    print_error "Left employee cleanup failed!"
    # Show last few lines of error log
    echo ""
    print_info "Last 10 lines of log:"
    tail -n 10 "$LOG_FILE" 2>/dev/null || echo "Could not read log file"
fi

print_info "Check full log: $LOG_FILE"

exit $RESULT