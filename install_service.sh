#!/bin/bash

# ImprovMX Webhook Service Installer
# This script installs the systemd service for the ImprovMX webhook server

set -e

echo "=========================================="
echo "ImprovMX Webhook Service Installer"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Error: This script must be run as root (use sudo)"
    echo "   Usage: sudo ./install_service.sh"
    exit 1
fi

# Configuration
SERVICE_NAME="improvmx-webhook"
SERVICE_FILE="$SERVICE_NAME.service"
INSTALL_DIR="/home/jose/webmail_improvmx"
VENV_DIR="$INSTALL_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"
VIRTUALENV_USER="jose"
VIRTUALENV_GROUP="jose"

echo "📋 Installation Configuration:"
echo "   Service Name: $SERVICE_NAME"
echo "   Installation Directory: $INSTALL_DIR"
echo "   Virtual Environment: $VENV_DIR"
echo "   Systemd Directory: $SYSTEMD_DIR"
echo "   Run as User: $VIRTUALENV_USER"
echo ""

# Check if installation directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Error: Installation directory does not exist: $INSTALL_DIR"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "❌ Error: .env file not found in $INSTALL_DIR"
    exit 1
fi

echo "✅ Installation directory found"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
echo "✅ Dependencies installed"

# Verify gunicorn installation
echo "🔍 Verifying gunicorn installation..."
if [ ! -f "$VENV_DIR/bin/gunicorn" ]; then
    echo "⚠️  Warning: gunicorn not found in virtual environment"
    echo "   Installing gunicorn explicitly..."
    "$VENV_DIR/bin/pip" install gunicorn
fi

if [ -f "$VENV_DIR/bin/gunicorn" ]; then
    GUNICORN_VERSION=$("$VENV_DIR/bin/gunicorn" --version)
    echo "✅ Gunicorn installed: $GUNICORN_VERSION"
else
    echo "❌ Error: gunicorn installation failed"
    echo "   Checking Python and pip version..."
    "$VENV_DIR/bin/python3" --version
    "$VENV_DIR/bin/pip" --version
    echo "   Listing installed packages:"
    "$VENV_DIR/bin/pip" list
    exit 1
fi

# Check if MongoDB is running
echo "🔍 Checking MongoDB connection..."
if ! systemctl is-active --quiet mongod.service; then
    echo "⚠️  Warning: MongoDB service is not running"
    echo "   Starting MongoDB..."
    systemctl start mongod.service
    sleep 2
fi

# Test MongoDB connection with credentials from .env (using virtual environment)
echo "🔍 Testing MongoDB connection..."
cd "$INSTALL_DIR"
export $(cat .env | grep -v '^#' | xargs)
"$VENV_DIR/bin/python3" -c "
from pymongo import MongoClient
import os
import sys
try:
    MONGO_URI = f\"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}\"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.server_info()
    print('✅ MongoDB connection successful')
except Exception as e:
    print(f'❌ MongoDB connection failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ MongoDB connection test failed. Please check your .env configuration"
    exit 1
fi

# Set ownership of virtual environment
echo "🔧 Setting ownership..."
chown -R $VIRTUALENV_USER:$VIRTUALENV_GROUP "$VENV_DIR"
chown -R $VIRTUALENV_USER:$VIRTUALENV_GROUP "$INSTALL_DIR"
echo "✅ Ownership set to $VIRTUALENV_USER:$VIRTUALENV_GROUP"

# Test gunicorn execution manually first
echo "🧪 Testing gunicorn execution manually..."
cd "$INSTALL_DIR"
export $(cat .env | grep -v '^#' | xargs)
echo "   Running: $VENV_DIR/bin/gunicorn --version"
"$VENV_DIR/bin/gunicorn" --version
echo "✅ Gunicorn can execute successfully"

# Copy service file to systemd directory
echo "📋 Installing systemd service..."
cp "$INSTALL_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_FILE"
echo "✅ Service file installed to $SYSTEMD_DIR/$SERVICE_FILE"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# Enable service to start on boot
echo "🚀 Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"
echo "✅ Service enabled"

# Stop existing service if running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⏹️  Stopping existing service..."
    systemctl stop "$SERVICE_NAME"
    sleep 2
fi

# Start service
echo "🚀 Starting service..."
systemctl start "$SERVICE_NAME"
sleep 2

# Check service status
echo ""
echo "📊 Service Status:"
systemctl status "$SERVICE_NAME" --no-pager -l
echo ""

# Check if service is running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Service is running successfully!"
else
    echo "❌ Service failed to start. Check logs with: journalctl -u $SERVICE_NAME"
    exit 1
fi

# Test health endpoint
echo "🔍 Testing health endpoint..."
sleep 2
HEALTH_CHECK=$(curl -s http://localhost:42010/ 2>/dev/null || echo "failed")
if [[ "$HEALTH_CHECK" == *"healthy"* ]]; then
    echo "✅ Health check passed - Webhook is responding"
else
    echo "⚠️  Health check failed - Service may not be responding correctly"
    echo "   Check logs with: journalctl -u $SERVICE_NAME -f"
fi

echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "📚 Useful Commands:"
echo "   Status:    sudo systemctl status $SERVICE_NAME"
echo "   Start:     sudo systemctl start $SERVICE_NAME"
echo "   Stop:      sudo systemctl stop $SERVICE_NAME"
echo "   Restart:   sudo systemctl restart $SERVICE_NAME"
echo "   Logs:      sudo journalctl -u $SERVICE_NAME -f"
echo "   Reload:    sudo systemctl reload $SERVICE_NAME"
echo ""
echo "🔗 Webhook is listening on: http://localhost:42010"
echo "   (Accessible via HTTPS through Caddy)"
echo ""
echo "📝 Configuration:"
echo "   Service file: $SYSTEMD_DIR/$SERVICE_NAME"
echo "   Working dir:  $INSTALL_DIR"
echo "   Environment:  $INSTALL_DIR/.env"
echo ""