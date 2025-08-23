#!/bin/bash

# ERPNext Sync All Manual Status Script
# Comprehensive status checking for all sync processes

SCRIPT_NAME="erpnext_sync_all.py"
SERVICE_NAME="erpnext-sync-all"
PID_FILE="erpnext_sync_all.pid"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$APP_DIR"

echo "📊 ERPNext Sync Status Check"
echo "============================="
echo "Script directory: $APP_DIR"
echo "Timestamp: $(date)"
echo ""

# Function to show note about systemd service removal
show_systemd_note() {
    echo "ℹ️  Systemd Service: REMOVED (using manual scripts only)"
    echo "   📋 Note: systemd service files were removed in favor of manual scripts"
    echo "   🎯 Use manual scripts for full control and better diagnostics"
}

# Function to check manual processes
check_manual_processes() {
    echo ""
    echo "🖥️  Manual Process Status:"
    
    local processes=$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)
    if [ ! -z "$processes" ]; then
        echo "   🟢 Status: RUNNING"
        echo "   🆔 PIDs: $processes"
        echo ""
        echo "   📋 Process Details:"
        
        # Show detailed process information
        ps aux | grep -E "python.*$SCRIPT_NAME" | grep -v grep | while read line; do
            echo "      $line"
        done
        
        # Show process tree if available
        if command -v pstree >/dev/null 2>&1; then
            echo ""
            echo "   🌳 Process Tree:"
            for pid in $processes; do
                echo "      PID $pid:"
                pstree -p "$pid" 2>/dev/null | sed 's/^/        /' || echo "        Process tree not available for PID $pid"
            done
        fi
        
        return 0
    else
        echo "   ⚪ Status: NOT RUNNING"
        return 1
    fi
}

# Function to check PID file status
check_pid_file() {
    echo ""
    echo "📄 PID File Status:"
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        echo "   📁 File: EXISTS ($PID_FILE)"
        echo "   🆔 PID: $pid"
        
        if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "   ✅ Process: RUNNING"
            
            # Show process start time
            local start_time=$(ps -o lstart= -p "$pid" 2>/dev/null)
            if [ ! -z "$start_time" ]; then
                echo "   ⏰ Started: $start_time"
            fi
            
            return 0
        else
            echo "   ❌ Process: NOT RUNNING (stale PID file)"
            return 1
        fi
    else
        echo "   ⚪ File: NOT FOUND"
        return 1
    fi
}

# Function to check log files
check_log_files() {
    echo ""
    echo "📋 Log Files Status:"
    
    local log_dir="$APP_DIR/logs"
    if [ -d "$log_dir" ]; then
        echo "   📁 Logs directory: EXISTS"
        
        # Check main log files
        local files=("logs.log" "error.log" "service.log" "service_error.log" "status.json")
        for file in "${files[@]}"; do
            local filepath="$log_dir/$file"
            if [ -f "$filepath" ]; then
                local size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null)
                local modified=$(stat -f%Sm "$filepath" 2>/dev/null || stat -c%y "$filepath" 2>/dev/null | cut -d' ' -f1-2)
                echo "   📄 $file: ${size} bytes, modified: $modified"
            else
                echo "   📄 $file: NOT FOUND"
            fi
        done
        
        # Show recent log entries if available
        if [ -f "$log_dir/logs.log" ] && [ -s "$log_dir/logs.log" ]; then
            echo ""
            echo "   📝 Recent Success Log (last 3 lines):"
            tail -3 "$log_dir/logs.log" | sed 's/^/      /'
        fi
        
        if [ -f "$log_dir/error.log" ] && [ -s "$log_dir/error.log" ]; then
            echo ""
            echo "   ⚠️  Recent Error Log (last 3 lines):"
            tail -3 "$log_dir/error.log" | sed 's/^/      /'
        fi
    else
        echo "   📁 Logs directory: NOT FOUND"
    fi
}

# Function to check device connectivity
check_device_connectivity() {
    echo ""
    echo "🌐 Device Connectivity Status:"
    
    # Try to read device configuration
    local config_check=$(python3 -c "
import sys
sys.path.append('$APP_DIR')
try:
    import local_config
    devices = local_config.devices
    print(f'DEVICES_COUNT:{len(devices)}')
    for i, device in enumerate(devices):
        print(f'DEVICE_{i}:{device[\"device_id\"]}:{device[\"ip\"]}')
except Exception as e:
    print(f'CONFIG_ERROR:{e}')
" 2>/dev/null)
    
    if echo "$config_check" | grep -q "CONFIG_ERROR"; then
        echo "   ❌ Configuration: ERROR reading local_config.py"
        echo "      $(echo "$config_check" | sed 's/CONFIG_ERROR://')"
        return 1
    elif echo "$config_check" | grep -q "DEVICES_COUNT"; then
        local device_count=$(echo "$config_check" | grep "DEVICES_COUNT" | cut -d':' -f2)
        echo "   📊 Configured devices: $device_count"
        
        # Test connectivity to each device
        echo "$config_check" | grep "DEVICE_" | while IFS=':' read -r prefix device_id ip; do
            echo -n "   🔍 Testing $device_id ($ip): "
            if ping -c 1 -W 2 "$ip" >/dev/null 2>&1; then
                echo -n "✅ PING OK"
                # Test ZK port if nc is available
                if command -v nc >/dev/null 2>&1; then
                    if timeout 3 nc -z "$ip" 4370 >/dev/null 2>&1; then
                        echo " | ✅ PORT 4370 OK"
                    else
                        echo " | ❌ PORT 4370 FAILED"
                    fi
                else
                    echo ""
                fi
            else
                echo "❌ PING FAILED"
            fi
        done
    else
        echo "   ⚪ No device configuration found"
    fi
}

# Function to show resource usage
show_resource_usage() {
    echo ""
    echo "⚡ Resource Usage:"
    
    local processes=$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)
    if [ ! -z "$processes" ]; then
        echo "   📊 Process Resources:"
        
        for pid in $processes; do
            if kill -0 "$pid" 2>/dev/null; then
                local cpu_mem=$(ps -o pid,pcpu,pmem,vsz,rss,etime,cmd -p "$pid" 2>/dev/null | tail -n +2)
                echo "      PID $pid: $cpu_mem"
            fi
        done
        
        # Show total resource usage
        local total_mem=$(ps -o pid,rss -p $processes 2>/dev/null | tail -n +2 | awk '{sum += $2} END {print sum}')
        if [ ! -z "$total_mem" ] && [ "$total_mem" != "0" ]; then
            local total_mem_mb=$((total_mem / 1024))
            echo "   💾 Total Memory: ${total_mem_mb}MB"
        fi
    else
        echo "   ⚪ No processes running"
    fi
}

# Function to show quick summary
show_summary() {
    echo ""
    echo "📋 SUMMARY:"
    echo "==========="
    
    # Quick status check
    local manual_running=false
    local pid_valid=false
    
    if [ ! -z "$(pgrep -f "$SCRIPT_NAME" 2>/dev/null)" ]; then
        manual_running=true
    fi
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            pid_valid=true
        fi
    fi
    
    # Overall status
    if [ "$manual_running" = true ]; then
        echo "   🟢 Overall Status: ACTIVE"
        echo "   🖥️  Running via: MANUAL PROCESS"
        echo ""
        echo "   🛑 To stop service:"
        echo "      Manual:  ./stop_erpnext_sync_all_manual.sh"
    else
        echo "   ⚪ Overall Status: INACTIVE"
        echo "   ⚪ Running via: NONE"
        echo ""
        echo "   🚀 To start service:"
        echo "      Manual:  ./start_erpnext_sync_all_manual.sh"
    fi
}

# Main execution
echo "🔍 Gathering status information..."
echo ""

# Run all checks
manual_status=0
pid_status=0

show_systemd_note
check_manual_processes || manual_status=1
check_pid_file || pid_status=1
check_log_files
check_device_connectivity
show_resource_usage
show_summary

echo ""
echo "📋 Useful commands:"
echo "   Current status: ./status_erpnext_sync_all_manual.sh"
echo "   Process details: ps aux | grep '$SCRIPT_NAME'"
echo "   Live logs: tail -f logs/logs.log"
echo "   Error logs: tail -f logs/error.log"
echo "   Start manual: ./start_erpnext_sync_all_manual.sh"
echo "   Stop manual: ./stop_erpnext_sync_all_manual.sh"
echo ""

# Exit with appropriate code
if [ $manual_status -eq 0 ]; then
    exit 0  # Something is running
else
    exit 1  # Nothing is running
fi