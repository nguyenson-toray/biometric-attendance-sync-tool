#!/bin/bash
#
# ERPNext Sync All Service Manager (Auto Password)
# Automatically provides sudo password for service management commands
#

# IMPORTANT: Set your sudo password here
SUDO_PASSWORD="T0ray25#"

# Service manager script path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_MANAGER="$SCRIPT_DIR/service_manager.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if service_manager.sh exists
if [ ! -f "$SERVICE_MANAGER" ]; then
    print_error "Service manager script not found: $SERVICE_MANAGER"
    exit 1
fi

# Commands that need sudo
SUDO_COMMANDS=("install" "uninstall" "start" "stop" "restart")

# Check if command needs sudo
needs_sudo() {
    local cmd="$1"
    for sudo_cmd in "${SUDO_COMMANDS[@]}"; do
        if [ "$cmd" = "$sudo_cmd" ]; then
            return 0
        fi
    done
    return 1
}

# Main logic
if [ -z "$1" ]; then
    # No command provided, show help
    "$SERVICE_MANAGER"
    exit 0
fi

COMMAND="$1"

if needs_sudo "$COMMAND"; then
    print_info "Running command with sudo: $COMMAND"
    echo "$SUDO_PASSWORD" | sudo -S "$SERVICE_MANAGER" "$@"
else
    # Commands that don't need sudo (status, logs, help)
    "$SERVICE_MANAGER" "$@"
fi
