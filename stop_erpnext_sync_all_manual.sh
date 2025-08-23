#!/bin/bash

# ERPNext Sync All Manual Stop Script
# Enhanced with force kill capabilities and comprehensive process cleanup

SCRIPT_NAME="erpnext_sync_all.py"
SERVICE_NAME="erpnext-sync-all"
PID_FILE="erpnext_sync_all.pid"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$APP_DIR"

echo "🛑 ERPNext Sync Manual Stop Script"
echo "==================================="
echo "Script directory: $APP_DIR"
echo "Timestamp: $(date)"
echo ""

# Function to force kill all related processes
force_kill_all_processes() {
    echo "🔥 FORCE KILLING all ERPNext sync processes..."
    echo ""
    
    local killed_count=0
    
    # Find all related processes
    local processes=$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)
    local systemd_pid=""
    
    # Check systemd service PID
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemd_pid=$(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null)
        echo "📋 Found systemd service PID: $systemd_pid"
    fi
    
    if [ ! -z "$processes" ]; then
        echo "📋 Found manual process PIDs: $processes"
        echo ""
        echo "📋 Process details before killing:"
        ps aux | grep -E "python.*$SCRIPT_NAME" | grep -v grep | while read line; do
            echo "   $line"
        done
        echo ""
        
        # Kill processes with escalating force
        echo "🔄 Step 1: Attempting graceful shutdown (SIGTERM)..."
        for pid in $processes; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -TERM "$pid" 2>/dev/null && echo "   Sent SIGTERM to PID: $pid"
            fi
        done
        
        sleep 3
        
        echo "🔄 Step 2: Force killing remaining processes (SIGKILL)..."
        for pid in $processes; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null && echo "   Sent SIGKILL to PID: $pid" && killed_count=$((killed_count + 1))
            else
                echo "   PID $pid already terminated"
                killed_count=$((killed_count + 1))
            fi
        done
    fi
    
    # Handle systemd service if running
    if [ ! -z "$systemd_pid" ] && [ "$systemd_pid" != "0" ]; then
        echo ""
        echo "🔄 Step 3: Stopping systemd service..."
        if systemctl stop "$SERVICE_NAME" 2>/dev/null; then
            echo "   ✅ Systemd service stopped successfully"
            killed_count=$((killed_count + 1))
        else
            echo "   ⚠️  Warning: Could not stop systemd service (may require sudo)"
            echo "   Manual command: sudo systemctl stop $SERVICE_NAME"
        fi
    fi
    
    # Final cleanup with pkill
    echo ""
    echo "🔄 Step 4: Final cleanup with pkill..."
    if pkill -KILL -f "$SCRIPT_NAME" 2>/dev/null; then
        echo "   ✅ Additional processes cleaned up with pkill"
        killed_count=$((killed_count + 1))
    else
        echo "   ✅ No additional processes found by pkill"
    fi
    
    # Clean up PID file
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        echo "   ✅ Cleaned up PID file: $PID_FILE"
    fi
    
    echo ""
    if [ $killed_count -gt 0 ]; then
        echo "✅ FORCE KILL COMPLETED: $killed_count process(es) terminated"
    else
        echo "ℹ️  No processes were running"
    fi
    
    return $killed_count
}

# Function for graceful stop
graceful_stop() {
    echo "🔄 Attempting graceful stop..."
    echo ""
    
    local stopped_count=0
    
    # Stop via PID file first
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        echo "📋 Found PID file with PID: $pid"
        
        if kill -0 "$pid" 2>/dev/null; then
            echo "   Process is running - sending SIGTERM..."
            if kill -TERM "$pid" 2>/dev/null; then
                echo "   ✅ Graceful shutdown signal sent"
                
                # Wait up to 10 seconds for graceful shutdown
                for i in {1..10}; do
                    if ! kill -0 "$pid" 2>/dev/null; then
                        echo "   ✅ Process terminated gracefully after ${i}s"
                        rm -f "$PID_FILE"
                        stopped_count=1
                        break
                    fi
                    sleep 1
                    echo -n "."
                done
                echo ""
                
                if kill -0 "$pid" 2>/dev/null; then
                    echo "   ⚠️  Process did not respond to graceful shutdown"
                    return 0
                fi
            else
                echo "   ❌ Failed to send termination signal"
                return 0
            fi
        else
            echo "   ⚠️  Process with PID $pid is not running"
            rm -f "$PID_FILE"
            echo "   ✅ Cleaned up stale PID file"
        fi
    else
        echo "📋 No PID file found - checking for running processes..."
        
        # Look for running processes
        local processes=$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)
        if [ ! -z "$processes" ]; then
            echo "   Found processes: $processes"
            echo "   These may be systemd-managed or started by other methods"
            return 0
        else
            echo "   ✅ No running processes found"
            stopped_count=1
        fi
    fi
    
    return $stopped_count
}

# Function to show current status
show_current_status() {
    echo "📊 Current Status Check:"
    echo ""
    
    # Check systemd service
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo "   🟢 Systemd service: ACTIVE"
        echo "      Status: $(systemctl show -p ActiveState --value "$SERVICE_NAME" 2>/dev/null)"
        echo "      PID: $(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null)"
    else
        echo "   ⚪ Systemd service: INACTIVE"
    fi
    
    # Check manual processes
    local processes=$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)
    if [ ! -z "$processes" ]; then
        echo "   🟢 Manual processes: RUNNING"
        echo "      PIDs: $processes"
        echo "      Details:"
        ps aux | grep -E "python.*$SCRIPT_NAME" | grep -v grep | while read line; do
            echo "        $line"
        done
    else
        echo "   ⚪ Manual processes: NOT RUNNING"
    fi
    
    # Check PID file
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "   🟢 PID file: VALID (PID: $pid)"
        else
            echo "   🟡 PID file: STALE (PID: $pid - not running)"
        fi
    else
        echo "   ⚪ PID file: NOT FOUND"
    fi
    echo ""
}

# Main execution
show_current_status

# Check if force flag is provided
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    force_kill_all_processes
    exit_code=$?
else
    # Try graceful stop first
    if graceful_stop; then
        echo "✅ Graceful stop completed successfully"
        exit_code=0
    else
        echo ""
        echo "⚠️  Graceful stop was not fully successful"
        echo ""
        echo "📋 Options:"
        echo "   1. Force kill all processes: $0 --force"
        echo "   2. Check what's still running: ps aux | grep '$SCRIPT_NAME'"
        echo "   3. Manual cleanup: pkill -f '$SCRIPT_NAME'"
        echo ""
        
        read -p "🤔 Would you like to force kill all processes now? (y/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            force_kill_all_processes
            exit_code=$?
        else
            echo "⏸️  Leaving remaining processes running"
            exit_code=1
        fi
    fi
fi

echo ""
echo "🎯 Final status:"
show_current_status

echo "📋 Useful commands:"
echo "   Check processes: ps aux | grep '$SCRIPT_NAME'"
echo "   Check systemd: sudo systemctl status $SERVICE_NAME"
echo "   View logs: tail logs/logs.log"
echo "   Force stop: $0 --force"
echo ""

exit $exit_code