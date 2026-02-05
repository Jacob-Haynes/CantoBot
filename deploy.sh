#!/bin/bash

# Automated Deployment Script for CantoBot on Raspberry Pi
# This script handles git pull, dependency installation, and service restart

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="cantonese_bot"
VENV_DIR=".venv"
PYTHON_VERSION="python3"

echo -e "${GREEN}=== CantoBot Deployment Script ===${NC}"
echo "Deployment directory: $SCRIPT_DIR"
echo ""

# Step 1: Check if running on Raspberry Pi (optional)
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo -e "${GREEN}[1/7]${NC} Detected device: $MODEL"
else
    echo -e "${YELLOW}[1/7]${NC} Not running on Raspberry Pi, continuing anyway..."
fi

# Step 2: Pull latest code from git
echo -e "${GREEN}[2/7]${NC} Pulling latest code from git..."
cd "$SCRIPT_DIR"

if [ -d .git ]; then
    git fetch origin
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" = "$REMOTE" ]; then
        echo "Already up to date."
    else
        echo "Updates available, pulling..."
        git pull
        echo -e "${GREEN}✓${NC} Code updated successfully"
    fi
else
    echo -e "${YELLOW}⚠${NC} Not a git repository, skipping pull"
fi

# Step 3: Check Python version
echo -e "${GREEN}[3/7]${NC} Checking Python version..."
PYTHON_CMD=$PYTHON_VERSION

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VER=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Using Python version: $PYTHON_VER"

# Step 4: Setup virtual environment
echo -e "${GREEN}[4/7]${NC} Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating new virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Step 5: Install/update dependencies
echo -e "${GREEN}[5/7]${NC} Installing dependencies..."
source "$VENV_DIR/bin/activate"

# Upgrade pip first
pip install --upgrade pip --quiet

# Install requirements
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓${NC} Dependencies installed successfully"

deactivate

# Step 6: Check if service exists and restart
echo -e "${GREEN}[6/7]${NC} Managing systemd service..."
if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    echo "Restarting $SERVICE_NAME service..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2

    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓${NC} Service restarted successfully"
    else
        echo -e "${RED}✗${NC} Service failed to start"
        sudo systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC} Service $SERVICE_NAME not found"
    echo "To install the service, run:"
    echo "  sudo cp cantonese_bot.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable $SERVICE_NAME"
    echo "  sudo systemctl start $SERVICE_NAME"
fi

# Step 7: Verify deployment
echo -e "${GREEN}[7/7]${NC} Verifying deployment..."

# Check if service is running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓${NC} Service is running"

    # Check health endpoint if configured
    if [ -f .env ]; then
        HEALTH_PORT=$(grep HEALTH_CHECK_PORT .env | cut -d '=' -f2 | tr -d ' ' || echo "8080")

        # Wait a bit for service to be fully ready
        sleep 3

        if command -v curl &> /dev/null; then
            echo "Checking health endpoint on port $HEALTH_PORT..."
            if curl -s "http://localhost:$HEALTH_PORT/health" > /dev/null; then
                HEALTH_RESPONSE=$(curl -s "http://localhost:$HEALTH_PORT/health")
                echo -e "${GREEN}✓${NC} Health check passed"
                echo "$HEALTH_RESPONSE" | grep -q '"healthy": true' && echo "  Status: Healthy" || echo "  Status: Degraded"
            else
                echo -e "${YELLOW}⚠${NC} Health endpoint not responding"
            fi
        fi
    fi

    echo ""
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo "To view logs, run: sudo journalctl -u $SERVICE_NAME -f"
else
    echo -e "${YELLOW}⚠${NC} Service is not running (may not be installed yet)"
    echo ""
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo "To run the bot manually: source .venv/bin/activate && python src/main.py"
fi
