#!/bin/bash
#
# Sync all users with fingerprints from master device to ERPNext
# Created: 2025-01-19
# Author: Biometric Attendance Sync Tool
#

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/12.sync_from_master_device_to_erpnext.py"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
LOG_DIR="$SCRIPT_DIR/logs/sync_from_master_device_to_erpnext"
LOG_FILE="$LOG_DIR/sync_master_device_to_erpnext.log"
ERROR_LOG="$LOG_DIR/sync_master_device_to_erpnext_error.log"
LOCK_FILE="/tmp/sync_master_device_to_erpnext.lock"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            echo "[$timestamp] [INFO] $message" >> "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" >&2
            echo "[$timestamp] [ERROR] $message" >> "$LOG_FILE"
            echo "[$timestamp] [ERROR] $message" >> "$ERROR_LOG"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            echo "[$timestamp] [WARN] $message" >> "$LOG_FILE"
            ;;
        "DEBUG")
            if [ "$VERBOSE" = "true" ]; then
                echo -e "${BLUE}[DEBUG]${NC} $message"
            fi
            echo "[$timestamp] [DEBUG] $message" >> "$LOG_FILE"
            ;;
    esac
}

# Function to check if script is already running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_message "ERROR" "Another sync process is already running (PID: $pid)"
            exit 1
        else
            log_message "WARN" "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
}

# Function to create lock
create_lock() {
    echo $$ > "$LOCK_FILE"
    log_message "DEBUG" "Created lock file with PID: $$"
}

# Function to remove lock
remove_lock() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        log_message "DEBUG" "Removed lock file"
    fi
}

# Function to setup logging directory
setup_logging() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        log_message "INFO" "Created log directory: $LOG_DIR"
    fi
    
    # Rotate logs if they get too large (>50MB)
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 52428800 ]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
        log_message "INFO" "Rotated log file"
    fi
    
    if [ -f "$ERROR_LOG" ] && [ $(stat -f%z "$ERROR_LOG" 2>/dev/null || stat -c%s "$ERROR_LOG" 2>/dev/null) -gt 52428800 ]; then
        mv "$ERROR_LOG" "$ERROR_LOG.old"
        log_message "INFO" "Rotated error log file"
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_message "DEBUG" "Checking prerequisites..."
    
    # Check if Python script exists
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        log_message "ERROR" "Python script not found: $PYTHON_SCRIPT"
        exit 1
    fi
    
    # Check if local_config.py exists
    if [ ! -f "$SCRIPT_DIR/local_config.py" ]; then
        log_message "ERROR" "Configuration file not found: $SCRIPT_DIR/local_config.py"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        log_message "ERROR" "Virtual environment not found: $VENV_DIR"
        log_message "ERROR" "Please create virtual environment: python3 -m venv venv"
        exit 1
    fi
    
    # Check if Python binary exists in venv
    if [ ! -f "$PYTHON_BIN" ]; then
        log_message "ERROR" "Python binary not found in virtual environment: $PYTHON_BIN"
        exit 1
    fi
    
    # Check if required Python modules are available in venv
    if ! "$PYTHON_BIN" -c "import pyzk, requests" &> /dev/null; then
        log_message "WARN" "Cannot verify Python modules availability in virtual environment"
        log_message "WARN" "If sync fails, ensure modules are installed in venv: $VENV_DIR/bin/pip install pyzk requests"
    fi
    
    # Check if erpnext_api_client.py exists
    if [ ! -f "$SCRIPT_DIR/erpnext_api_client.py" ]; then
        log_message "ERROR" "ERPNext API Client not found: $SCRIPT_DIR/erpnext_api_client.py"
        exit 1
    fi
    
    log_message "DEBUG" "Prerequisites check passed"
}

# Function to show usage
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [COMMAND]

Sync all users with fingerprints from master device to ERPNext (Active employees only).
Requires virtual environment at ./venv with required Python packages.

COMMANDS:
    sync            Sync all users from master device to ERPNext (default)
    test            Test connectivity to master device and ERPNext
    status          Show current sync status
    help            Show this help message

OPTIONS:
    -v, --verbose   Enable verbose output
    -l, --limit N   Limit sync to N users (for testing)
    --dry-run       Show what would be synced without actually syncing
    --no-lock       Skip lock file check (use with caution)

EXAMPLES:
    $0                          # Sync all users
    $0 sync                     # Same as above
    $0 -v sync                  # Sync with verbose output
    $0 --limit 10 sync          # Sync only first 10 users
    $0 test                     # Test connectivity
    $0 status                   # Show sync status

LOGS:
    Main log:    $LOG_FILE
    Error log:   $ERROR_LOG

SETUP:
    Create virtual environment: python3 -m venv venv
    Install packages: venv/bin/pip install pyzk requests

EOF
}

# Function to show sync status
show_status() {
    log_message "INFO" "=== Sync Status ==="
    
    if [ -f "$LOG_FILE" ]; then
        log_message "INFO" "Last log entries:"
        tail -n 10 "$LOG_FILE" | while IFS= read -r line; do
            echo "  $line"
        done
    else
        log_message "WARN" "No log file found"
    fi
    
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_message "INFO" "Sync process is currently running (PID: $pid)"
        else
            log_message "WARN" "Stale lock file found (PID: $pid)"
        fi
    else
        log_message "INFO" "No sync process is currently running"
    fi
}

# Function to run sync
run_sync() {
    local limit_arg=""
    local dry_run_arg=""
    
    if [ -n "$LIMIT" ]; then
        limit_arg="--limit $LIMIT"
    fi
    
    if [ "$DRY_RUN" = "true" ]; then
        log_message "INFO" "DRY RUN MODE - No actual syncing will be performed"
        dry_run_arg="--dry-run"
    fi
    
    log_message "INFO" "Starting fingerprint sync from master device to ERPNext (Active employees only)..."
    log_message "INFO" "Script: $PYTHON_SCRIPT"
    log_message "INFO" "Args: $limit_arg $dry_run_arg"
    
    # Run the Python script using virtual environment
    if [ "$VERBOSE" = "true" ]; then
        "$PYTHON_BIN" "$PYTHON_SCRIPT" $limit_arg $dry_run_arg 2>&1 | tee -a "$LOG_FILE"
    else
        "$PYTHON_BIN" "$PYTHON_SCRIPT" $limit_arg $dry_run_arg >> "$LOG_FILE" 2>&1
    fi
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_message "INFO" "Sync completed successfully"
    else
        log_message "ERROR" "Sync failed with exit code: $exit_code"
    fi
    
    return $exit_code
}

# Function to run connectivity test
run_test() {
    log_message "INFO" "Running connectivity test..."
    
    # Test master device connectivity
    "$PYTHON_BIN" -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
import local_config as config
from zk import ZK

# Test master device
master = config.devices_master
print(f'Testing master device: {master[\"device_id\"]} ({master[\"ip\"]})')
zk = ZK(master['ip'], port=4370, timeout=5)
try:
    conn = zk.connect()
    if conn:
        print('✅ Master device connected')
        users = conn.get_users()
        print(f'📊 Found {len(users)} users on master device')
        conn.disconnect()
    else:
        print('❌ Master device failed to connect')
        sys.exit(1)
except Exception as e:
    print(f'❌ Master device error: {e}')
    sys.exit(1)

# Test ERPNext API
import requests
try:
    url = f'{config.ERPNEXT_URL}/api/method/frappe.auth.get_logged_user'
    headers = {
        'Authorization': f'token {config.ERPNEXT_API_KEY}:{config.ERPNEXT_API_SECRET}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        user_data = response.json()
        print(f'✅ ERPNext API connected as: {user_data.get(\"message\", \"Unknown user\")}')
    else:
        print(f'❌ ERPNext API failed: HTTP {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'❌ ERPNext API error: {e}')
    sys.exit(1)

print('✅ All connectivity tests passed')
" 2>&1 | tee -a "$LOG_FILE"
        
    return ${PIPESTATUS[0]}
}

# Cleanup function
cleanup() {
    log_message "DEBUG" "Cleaning up..."
    remove_lock
}

# Trap cleanup on exit
trap cleanup EXIT INT TERM

# Parse command line arguments
COMMAND=""
VERBOSE=false
LIMIT=""
DRY_RUN=false
NO_LOCK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-lock)
            NO_LOCK=true
            shift
            ;;
        sync|test|status|help)
            COMMAND="$1"
            shift
            ;;
        -h|--help)
            COMMAND="help"
            shift
            ;;
        *)
            log_message "ERROR" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Default command
if [ -z "$COMMAND" ]; then
    COMMAND="sync"
fi

# Setup logging
setup_logging

# Log script start
log_message "INFO" "=== Script started: $(date) ==="
log_message "INFO" "Command: $COMMAND"
log_message "INFO" "Verbose: $VERBOSE"
if [ -n "$LIMIT" ]; then
    log_message "INFO" "Limit: $LIMIT users"
fi
if [ "$DRY_RUN" = "true" ]; then
    log_message "INFO" "Mode: DRY RUN"
fi

# Execute command
case "$COMMAND" in
    "sync")
        if [ "$NO_LOCK" != "true" ]; then
            check_lock
            create_lock
        fi
        check_prerequisites
        run_sync
        exit_code=$?
        ;;
    "test")
        check_prerequisites
        run_test
        exit_code=$?
        ;;
    "status")
        show_status
        exit_code=0
        ;;
    "help")
        show_help
        exit_code=0
        ;;
    *)
        log_message "ERROR" "Unknown command: $COMMAND"
        show_help
        exit_code=1
        ;;
esac

log_message "INFO" "=== Script finished: $(date) ==="
exit $exit_code