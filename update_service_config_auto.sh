#!/bin/bash
#
# Update systemd service configuration and restart (Auto Password)
# Automatically provides sudo password
#

# IMPORTANT: Set your sudo password here
SUDO_PASSWORD="T0ray25#"

echo "🔄 Updating ERPNext Sync Service Configuration..."

# Copy updated service file
echo "📋 Copying service file to systemd..."
echo "$SUDO_PASSWORD" | sudo -S cp erpnext-sync-all.service /etc/systemd/system/

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
echo "$SUDO_PASSWORD" | sudo -S systemctl daemon-reload

# Restart the service
echo "🚀 Restarting service..."
echo "$SUDO_PASSWORD" | sudo -S systemctl restart erpnext-sync-all

# Wait a moment for startup
sleep 3

# Show status
echo "📊 Service status:"
echo "$SUDO_PASSWORD" | sudo -S systemctl status erpnext-sync-all --no-pager

echo ""
echo "📝 Recent service logs:"
echo "$SUDO_PASSWORD" | sudo -S journalctl -u erpnext-sync-all -n 10 --no-pager

echo ""
echo "📝 Service wrapper logs:"
tail -n 10 logs/service.log 2>/dev/null || echo "No service.log found"

echo ""
echo "✅ Service configuration updated!"
echo "💡 Use './service_manager_auto.sh logs follow' to monitor logs"
