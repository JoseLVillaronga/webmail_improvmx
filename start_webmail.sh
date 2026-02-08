#!/bin/bash

# Webmail Application Startup Script

echo "Starting Webmail Application..."
echo "======================================"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "Environment variables loaded from .env"
else
    echo "Warning: .env file not found in current directory"
fi

# Check if MongoDB is running
echo "Checking MongoDB connection..."
cd webmail
python3 -c "
from pymongo import MongoClient
import os
try:
    MONGO_URI = f\"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@{os.getenv('MONGO_HOST')}\"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    client.server_info()
    print('✓ MongoDB connection successful')
except Exception as e:
    print(f'✗ MongoDB connection failed: {e}')
    print('Please ensure MongoDB is running and credentials are correct')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "MongoDB connection failed. Exiting."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment..."
    cd ..
    python3 -m venv venv
    cd webmail
fi

echo "Installing dependencies..."
source ../venv/bin/activate
pip install -q -r ../requirements.txt

# Start Gunicorn server
echo "Starting Gunicorn server on port 26000..."
echo "Press Ctrl+C to stop the server"
echo "======================================"

gunicorn -c gunicorn.conf.py app:app