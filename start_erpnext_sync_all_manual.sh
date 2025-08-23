#!/bin/bash

# ERPNext Sync All Manual Start Script
# Enhanced with comprehensive process checking and warnings

SCRIPT_NAME="erpnext_sync_all.py"
SERVICE_NAME="erpnext-sync-all"
PID_FILE="erpnext_sync_all.pid"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$APP_DIR"

echo "🚀 ERPNext Sync Manual Start Script"
echo "===================================="
echo "Script directory: $APP_DIR"
echo "Timestamp: $(date)"
echo ""

# Function to show note about systemd service removal
show_systemd_note() {
    echo "ℹ️  Note: systemd service was removed - using manual scripts only"
    echo "   🎯 This provides better control and diagnostics"
}

# Function to check for running processes
check_running_processes() {
    local processes=$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)
    if [ ! -z "$processes" ]; then
        echo "⚠️  WARNING: Found existing $SCRIPT_NAME processes!"
        echo "   PIDs: $processes"
        echo ""
        echo "📋 Process details:"
        ps aux | grep -E "python.*$SCRIPT_NAME" | grep -v grep | while read line; do
            echo "   $line"
        done
        echo ""
        echo "🛑 CONFLICT DETECTED: Multiple instances will cause device connection conflicts."
        echo ""
        echo "📋 Options:"
        echo "   1. Stop existing processes: ./stop_erpnext_sync_all_manual.sh"
        echo "   2. Kill all processes: pkill -f '$SCRIPT_NAME'"
        echo "   3. Check process details: ps aux | grep '$SCRIPT_NAME'"
        echo ""
        return 1
    fi
}

# Function to check device connectivity
check_device_status() {
    echo "🔍 Checking device connectivity..."
    local config_devices=$(python3 -c "import local_config; print(len(local_config.devices))" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "   Configured devices: $config_devices"
        
        # Test basic connectivity to first device
        local first_ip=$(python3 -c "import local_config; print(local_config.devices[0]['ip'] if local_config.devices else 'N/A')" 2>/dev/null)
        if [ "$first_ip" != "N/A" ] && [ ! -z "$first_ip" ]; then
            if ping -c 1 -W 2 "$first_ip" >/dev/null 2>&1; then
                echo "   Sample device ($first_ip): ✅ Reachable"
            else
                echo "   Sample device ($first_ip): ❌ Not reachable"
                echo "   ⚠️  Warning: Network connectivity issues detected"
            fi
        fi
    else
        echo "   ❌ Cannot read device configuration"
    fi
    echo ""
}

# Function to validate environment
validate_environment() {
    echo "🔧 Validating environment..."
    
    # Check if venv exists
    if [ ! -f "venv/bin/python3" ]; then
        echo "   ❌ Virtual environment not found: venv/bin/python3"
        echo "   Please ensure the virtual environment is properly set up."
        return 1
    else
        echo "   ✅ Virtual environment found"
    fi
    
    # Check if script exists
    if [ ! -f "$SCRIPT_NAME" ]; then
        echo "   ❌ Script not found: $SCRIPT_NAME"
        return 1
    else
        echo "   ✅ Script found: $SCRIPT_NAME"
    fi
    
    # Check if config exists
    if [ ! -f "local_config.py" ]; then
        echo "   ❌ Configuration file not found: local_config.py"
        return 1
    else
        echo "   ✅ Configuration file found"
    fi
    
    echo ""
    return 0
}

# Main execution
echo "🔍 Performing pre-start checks..."
echo ""

show_systemd_note
echo ""

# Check running processes
if ! check_running_processes; then
    echo "❌ Cannot start: existing process conflict detected"
    exit 1
fi

# Validate environment
if ! validate_environment; then
    echo "❌ Cannot start: environment validation failed"
    exit 1
fi

# Check device status (informational)
check_device_status

# All checks passed - start the service
echo "✅ All pre-start checks passed!"
echo ""
echo "🚀 Starting ERPNext sync service..."
echo "   Command: venv/bin/python3 $SCRIPT_NAME"
echo "   Working directory: $APP_DIR"
echo "   Started at: $(date)"
echo ""

# Start the process in background
venv/bin/python3 "$SCRIPT_NAME" &
PROCESS_PID=$!

# Save PID and verify process started
echo "$PROCESS_PID" > "$PID_FILE"
sleep 2

# Verify the process is still running
if kill -0 "$PROCESS_PID" 2>/dev/null; then
    echo "✅ ERPNext sync service started successfully!"
    echo "   PID: $PROCESS_PID"
    echo "   PID file: $PID_FILE"
    echo ""
    echo "📋 Management commands:"
    echo "   Stop service: ./stop_erpnext_sync_all_manual.sh"
    echo "   Check status: ps -p $PROCESS_PID"
    echo "   View logs: tail -f logs/logs.log"
    echo "   View errors: tail -f logs/error.log"
    echo ""
    echo "🎯 Service is now running in background mode"
else
    echo "❌ Failed to start service - process exited immediately"
    rm -f "$PID_FILE"
    echo "   Check logs for errors: tail logs/error.log"
    exit 1
fi
