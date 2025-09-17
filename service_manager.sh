#!/bin/bash
#
# ERPNext Sync All Service Manager
# Script to install, enable, and manage the ERPNext sync service
#

SERVICE_NAME="erpnext-sync-all"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/$SERVICE_NAME.service"
SYSTEM_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
}

# Function to install the service
install_service() {
    print_header "🚀 Installing ERPNext Sync All Service"

    check_root

    # Check if service file exists
    if [ ! -f "$SERVICE_FILE" ]; then
        print_error "Service file not found: $SERVICE_FILE"
        exit 1
    fi

    # Copy service file to systemd directory
    print_status "Copying service file to $SYSTEM_SERVICE_PATH"
    cp "$SERVICE_FILE" "$SYSTEM_SERVICE_PATH"

    # Set correct permissions
    chmod 644 "$SYSTEM_SERVICE_PATH"

    # Reload systemd daemon
    print_status "Reloading systemd daemon"
    systemctl daemon-reload

    # Enable the service
    print_status "Enabling service to start at boot"
    systemctl enable "$SERVICE_NAME"

    print_status "✅ Service installed successfully!"
    print_status "You can now start it with: sudo systemctl start $SERVICE_NAME"
}

# Function to uninstall the service
uninstall_service() {
    print_header "🗑️ Uninstalling ERPNext Sync All Service"

    check_root

    # Stop the service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "Stopping service"
        systemctl stop "$SERVICE_NAME"
    fi

    # Disable the service
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        print_status "Disabling service"
        systemctl disable "$SERVICE_NAME"
    fi

    # Remove service file
    if [ -f "$SYSTEM_SERVICE_PATH" ]; then
        print_status "Removing service file"
        rm "$SYSTEM_SERVICE_PATH"
    fi

    # Reload systemd daemon
    print_status "Reloading systemd daemon"
    systemctl daemon-reload

    print_status "✅ Service uninstalled successfully!"
}

# Function to show service status
show_status() {
    print_header "📊 ERPNext Sync All Service Status"

    echo
    echo "Service Status:"
    systemctl status "$SERVICE_NAME" --no-pager

    echo
    echo "Recent Logs (last 20 lines):"
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager
}

# Function to start the service
start_service() {
    print_header "▶️ Starting ERPNext Sync All Service"

    check_root

    systemctl start "$SERVICE_NAME"

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "✅ Service started successfully!"
    else
        print_error "❌ Failed to start service"
        systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

# Function to stop the service
stop_service() {
    print_header "⏹️ Stopping ERPNext Sync All Service"

    check_root

    systemctl stop "$SERVICE_NAME"

    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "✅ Service stopped successfully!"
    else
        print_error "❌ Failed to stop service"
        exit 1
    fi
}

# Function to restart the service
restart_service() {
    print_header "🔄 Restarting ERPNext Sync All Service"

    check_root

    systemctl restart "$SERVICE_NAME"

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "✅ Service restarted successfully!"
    else
        print_error "❌ Failed to restart service"
        systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

# Function to show logs
show_logs() {
    print_header "📝 ERPNext Sync All Service Logs"

    case "$2" in
        "follow"|"f")
            print_status "Following logs (Press Ctrl+C to stop)..."
            journalctl -u "$SERVICE_NAME" -f
            ;;
        "tail")
            LINES=${3:-50}
            print_status "Showing last $LINES lines..."
            journalctl -u "$SERVICE_NAME" -n "$LINES" --no-pager
            ;;
        *)
            print_status "Showing last 50 lines (use 'follow' or 'tail N' for more options)..."
            journalctl -u "$SERVICE_NAME" -n 50 --no-pager
            ;;
    esac
}

# Function to show help
show_help() {
    echo "ERPNext Sync All Service Manager"
    echo "================================"
    echo
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  install    - Install and enable the service"
    echo "  uninstall  - Stop, disable and remove the service"
    echo "  start      - Start the service"
    echo "  stop       - Stop the service"
    echo "  restart    - Restart the service"
    echo "  status     - Show service status and recent logs"
    echo "  logs       - Show service logs"
    echo "  logs follow - Follow logs in real-time"
    echo "  logs tail N - Show last N lines of logs"
    echo "  help       - Show this help message"
    echo
    echo "Examples:"
    echo "  sudo $0 install"
    echo "  sudo $0 start"
    echo "  $0 status"
    echo "  $0 logs follow"
    echo "  $0 logs tail 100"
}

# Main script logic
case "$1" in
    "install")
        install_service
        ;;
    "uninstall")
        uninstall_service
        ;;
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$@"
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac