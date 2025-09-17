#!/bin/bash
#
# Update systemd service configuration and restart
#

echo "🔄 Updating ERPNext Sync Service Configuration..."

# Copy updated service file
echo "📋 Copying service file to systemd..."
sudo cp erpnext-sync-all.service /etc/systemd/system/

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Restart the service
echo "🚀 Restarting service..."
sudo systemctl restart erpnext-sync-all

# Wait a moment for startup
sleep 3

# Show status
echo "📊 Service status:"
sudo systemctl status erpnext-sync-all --no-pager

echo ""
echo "📝 Recent service logs:"
sudo journalctl -u erpnext-sync-all -n 10 --no-pager

echo ""
echo "📝 Service wrapper logs:"
tail -n 10 logs/service.log

echo ""
echo "✅ Service configuration updated!"
echo "💡 Use './service_manager.sh logs follow' to monitor logs"