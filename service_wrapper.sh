#!/bin/bash
#
# ERPNext Sync All Service Wrapper
# Wrapper script for systemd service to ensure proper environment and error handling
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/erpnext_sync_all.py"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
LOG_FILE="$SCRIPT_DIR/logs/service.log"

# Ensure logs directory exists
mkdir -p "$SCRIPT_DIR/logs"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to validate environment
validate_environment() {
    log "🔧 Validating service environment..."

    # Check if venv exists
    if [ ! -f "$VENV_PYTHON" ]; then
        log "❌ ERROR: Virtual environment not found: $VENV_PYTHON"
        return 1
    fi

    # Check if script exists
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        log "❌ ERROR: Python script not found: $PYTHON_SCRIPT"
        return 1
    fi

    # Check if config exists
    if [ ! -f "$SCRIPT_DIR/local_config.py" ]; then
        log "❌ ERROR: Configuration file not found: local_config.py"
        return 1
    fi

    # Test network connectivity to sample device
    log "🌐 Testing network connectivity..."

    # Debug network environment
    log "   Network debug info:"
    log "   - USER: $(whoami)"
    log "   - PATH: $PATH"
    log "   - Available ping: $(which ping 2>/dev/null || echo 'NOT FOUND')"

    # Try different ping approaches
    if /bin/ping -c 1 -W 2 10.0.1.41 >/dev/null 2>&1; then
        log "✅ Network connectivity test passed (/bin/ping to 10.0.1.41 successful)"
    elif /usr/bin/ping -c 1 -W 2 10.0.1.41 >/dev/null 2>&1; then
        log "✅ Network connectivity test passed (/usr/bin/ping to 10.0.1.41 successful)"
    else
        log "⚠️ WARNING: Network connectivity test failed (10.0.1.41 not reachable)"
        log "   This might cause device connection issues"
        log "   Service will continue but may have network problems"
    fi

    log "✅ Environment validation passed"
    return 0
}

# Function to handle cleanup on exit
cleanup() {
    log "🛑 Service wrapper received shutdown signal"
    # Kill the Python process if it's still running
    if [ ! -z "$PYTHON_PID" ] && kill -0 "$PYTHON_PID" 2>/dev/null; then
        log "   Terminating Python process (PID: $PYTHON_PID)"
        kill -TERM "$PYTHON_PID"
        # Wait for graceful shutdown
        sleep 5
        if kill -0 "$PYTHON_PID" 2>/dev/null; then
            log "   Force killing Python process"
            kill -KILL "$PYTHON_PID"
        fi
    fi
    log "🛑 Service wrapper shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Change to script directory
cd "$SCRIPT_DIR" || {
    log "❌ ERROR: Cannot change to script directory: $SCRIPT_DIR"
    exit 1
}

log "🚀 ERPNext Sync All Service Wrapper Started"
log "   Script directory: $SCRIPT_DIR"
log "   Python interpreter: $VENV_PYTHON"
log "   Target script: $PYTHON_SCRIPT"

# Validate environment
if ! validate_environment; then
    log "❌ Environment validation failed, exiting"
    exit 1
fi

# Remove any existing PID file
PID_FILE="$SCRIPT_DIR/erpnext_sync_all.pid"
if [ -f "$PID_FILE" ]; then
    log "🗑️ Removing existing PID file"
    rm -f "$PID_FILE"
fi

log "🎯 Starting ERPNext sync service..."

# Start the Python script
"$VENV_PYTHON" "$PYTHON_SCRIPT" &
PYTHON_PID=$!

# Save PID for monitoring
echo "$PYTHON_PID" > "$PID_FILE"
log "✅ ERPNext sync service started (PID: $PYTHON_PID)"

# Wait for the Python process to complete
wait "$PYTHON_PID"
EXIT_CODE=$?

# Clean up PID file
rm -f "$PID_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    log "✅ ERPNext sync service exited normally"
else
    log "❌ ERPNext sync service exited with error code: $EXIT_CODE"
fi

exit $EXIT_CODE