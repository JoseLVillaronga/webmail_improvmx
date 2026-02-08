#!/bin/bash

# ImprovMX Webhook Service Uninstaller
# This script removes the systemd service for ImprovMX webhook server

set -e

echo "=========================================="
echo "ImprovMX Webhook Service Uninstaller"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Error: This script must be run as root (use sudo)"
    echo "   Usage: sudo ./uninstall_service.sh"
    exit 1
fi

# Configuration
SERVICE_NAME="improvmx-webhook"
SERVICE_FILE="$SERVICE_NAME.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "⚠️  WARNING: This will stop and remove the $SERVICE_NAME service"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "❌ Uninstallation cancelled"
    exit 0
fi

echo ""
echo "🛑 Stopping service..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
    echo "✅ Service stopped"
else
    echo "ℹ️  Service was not running"
fi

echo ""
echo "🔄 Disabling service..."
if systemctl is-enabled --quiet "$SERVICE_NAME"; then
    systemctl disable "$SERVICE_NAME"
    echo "✅ Service disabled"
else
    echo "ℹ️  Service was not enabled"
fi

echo ""
echo "🗑️  Removing service file..."
if [ -f "$SYSTEMD_DIR/$SERVICE_FILE" ]; then
    rm "$SYSTEMD_DIR/$SERVICE_FILE"
    echo "✅ Service file removed"
else
    echo "ℹ️  Service file was not found"
fi

echo ""
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload
systemctl reset-failed
echo "✅ Systemd daemon reloaded"

echo ""
echo "=========================================="
echo "✅ Uninstallation Complete!"
echo "=========================================="
echo ""
echo "📝 Notes:"
echo "   - The systemd service has been removed"
echo "   - Virtual environment and application files remain intact"
echo "   - MongoDB data has not been affected"
echo "   - Logs in systemd journal are preserved"
echo ""
echo "🔍 To remove all data, you may also want to:"
echo "   - Remove the virtual environment: rm -rf /home/jose/webmail_improvmx/venv"
echo "   - Remove MongoDB data (if desired)"
echo "   - Clear systemd logs: journalctl --rotate && journalctl --vacuum-time=1d"
echo ""