#!/bin/bash
# Deployment script for 24 Hours of Lemons systems
# Usage: ./scripts/deploy.sh [drs|telemetry|all]

set -e  # Exit on error

# Configuration
DEPLOY_DIR="/opt/lemons"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAR_ID="${CAR_ID:-car1}"  # Default to car1

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
APPS="${1:-all}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}24 Hours of Lemons - Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Repository: $REPO_DIR"
echo "Deploy to: $DEPLOY_DIR"
echo "Car ID: $CAR_ID"
echo "Apps: $APPS"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: Not running on Raspberry Pi. Deployment may not work correctly.${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. Create deploy directory
echo -e "${GREEN}[1/5] Creating deployment directory...${NC}"
sudo mkdir -p "$DEPLOY_DIR"
sudo chown -R pi:pi "$DEPLOY_DIR"

# 2. Copy code
echo -e "${GREEN}[2/5] Copying code...${NC}"
rsync -av --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'logs' \
    --exclude '.venv' \
    "$REPO_DIR/" "$DEPLOY_DIR/"

# 3. Install Python dependencies
echo -e "${GREEN}[3/5] Installing dependencies...${NC}"
if [ ! -d "$DEPLOY_DIR/.venv" ]; then
    python3 -m venv "$DEPLOY_DIR/.venv"
fi

source "$DEPLOY_DIR/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$DEPLOY_DIR/requirements.txt"
deactivate

# 4. Create logs directory
mkdir -p "$DEPLOY_DIR/logs"

# 5. Deploy systemd services
echo -e "${GREEN}[4/5] Setting up systemd services...${NC}"

deploy_service() {
    local app=$1
    echo "  - Deploying $app service..."

    sudo cp "$DEPLOY_DIR/systemd/lemons@.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable "lemons@$app.service"

    # Restart service
    if sudo systemctl is-active --quiet "lemons@$app.service"; then
        echo "    Restarting $app..."
        sudo systemctl restart "lemons@$app.service"
    else
        echo "    Starting $app..."
        sudo systemctl start "lemons@$app.service"
    fi

    # Check status
    sleep 2
    if sudo systemctl is-active --quiet "lemons@$app.service"; then
        echo -e "    ${GREEN}✓ $app is running${NC}"
    else
        echo -e "    ${RED}✗ $app failed to start${NC}"
        sudo systemctl status "lemons@$app.service" --no-pager
    fi
}

if [ "$APPS" = "all" ]; then
    deploy_service "drs"
    deploy_service "telemetry"
elif [ "$APPS" = "drs" ] || [ "$APPS" = "telemetry" ]; then
    deploy_service "$APPS"
else
    echo -e "${RED}Error: Unknown app '$APPS'. Use: drs, telemetry, or all${NC}"
    exit 1
fi

# 6. Show service status
echo -e "\n${GREEN}[5/5] Deployment complete!${NC}\n"
echo "Service status:"
sudo systemctl status "lemons@*.service" --no-pager || true

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Quick commands:${NC}"
echo "  View logs:    journalctl -u lemons@drs -f"
echo "  View logs:    journalctl -u lemons@telemetry -f"
echo "  Restart:      sudo systemctl restart lemons@drs"
echo "  Stop:         sudo systemctl stop lemons@drs"
echo "  Check health: curl http://localhost:5001/healthz"
echo "  Dashboard:    http://$(hostname -I | awk '{print $1}'):5000"
echo -e "${GREEN}========================================${NC}\n"
