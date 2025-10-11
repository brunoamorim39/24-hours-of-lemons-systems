#!/bin/bash
# Remote deployment script for trackside Pi deployment
# Usage: ./remote-deploy.sh <host> <car_id>

set -e

HOST=$1
CAR_ID=$2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emojis for visual scanning
CHECK="✅"
CROSS="❌"
WARN="⚠️ "
ROCKET="🚀"
WRENCH="🔧"

if [ -z "$HOST" ] || [ -z "$CAR_ID" ]; then
    echo -e "${RED}${CROSS} Error: Missing arguments${NC}"
    echo "Usage: $0 <host> <car_id>"
    echo "Example: $0 192.168.1.100 car1"
    exit 1
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🏁 24 HOURS OF LEMONS - REMOTE DEPLOY    ║${NC}"
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo ""
echo -e "Target: ${GREEN}$HOST${NC}"
echo -e "Car ID: ${GREEN}$CAR_ID${NC}"
echo ""

# ============================================================================
# Step 1: Pre-flight checks
# ============================================================================

echo -e "${BLUE}[1/6]${NC} ${WRENCH} Pre-flight checks..."

# Ping test
echo -n "  • Testing connectivity... "
if ping -c 1 -W 2 $HOST &> /dev/null; then
    echo -e "${GREEN}${CHECK}${NC}"
else
    echo -e "${RED}${CROSS} Cannot reach $HOST${NC}"
    echo -e "${YELLOW}${WARN} Check network connection and Pi power${NC}"
    exit 1
fi

# SSH test
echo -n "  • Testing SSH access... "
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no pi@$HOST "echo test" &> /dev/null; then
    echo -e "${GREEN}${CHECK}${NC}"
else
    echo -e "${RED}${CROSS} Cannot SSH to pi@$HOST${NC}"
    echo -e "${YELLOW}${WARN} Ensure SSH is enabled on the Pi${NC}"
    echo -e "${YELLOW}${WARN} Default password is 'raspberry' if not changed${NC}"
    exit 1
fi

echo ""

# ============================================================================
# Step 2: Install git if needed
# ============================================================================

echo -e "${BLUE}[2/6]${NC} ${WRENCH} Checking git installation..."

ssh pi@$HOST "which git &> /dev/null" || {
    echo "  • Git not found, installing..."
    ssh pi@$HOST "sudo apt-get update -qq && sudo apt-get install -y git"
    echo -e "  ${GREEN}${CHECK} Git installed${NC}"
}

echo -e "  ${GREEN}${CHECK} Git available${NC}"
echo ""

# ============================================================================
# Step 3: Clone or update repository
# ============================================================================

echo -e "${BLUE}[3/6]${NC} ${ROCKET} Fetching code..."

# Check if repo already exists
if ssh pi@$HOST "[ -d ~/lemons ]"; then
    echo "  • Repository exists, updating..."
    ssh pi@$HOST "cd ~/lemons && git pull"
    echo -e "  ${GREEN}${CHECK} Code updated${NC}"
else
    echo "  • Cloning repository..."

    # Try HTTPS first (works for public repos)
    if ssh pi@$HOST "git clone https://github.com/your-org/24-hours-of-lemons-systems.git ~/lemons" 2>&1 | grep -q "Repository not found"; then
        echo -e "  ${YELLOW}${WARN} HTTPS clone failed (repo may be private)${NC}"
        echo "  • Trying SSH clone..."

        # Try SSH clone (requires deploy key on Pi)
        if ssh pi@$HOST "git clone git@github.com:your-org/24-hours-of-lemons-systems.git ~/lemons"; then
            echo -e "  ${GREEN}${CHECK} Code cloned via SSH${NC}"
        else
            echo -e "  ${RED}${CROSS} Failed to clone repository${NC}"
            echo ""
            echo -e "${YELLOW}${WARN} For private repos, set up a deploy key:${NC}"
            echo "  1. On Pi: ssh-keygen -t ed25519 -C 'lemons-deploy'"
            echo "  2. cat ~/.ssh/id_ed25519.pub"
            echo "  3. Add to GitHub: Settings → Deploy keys"
            echo ""
            echo -e "${YELLOW}${WARN} Or use HTTPS with token:${NC}"
            echo "  git clone https://TOKEN@github.com/your-org/24-hours-of-lemons-systems.git ~/lemons"
            exit 1
        fi
    else
        echo -e "  ${GREEN}${CHECK} Code cloned${NC}"
    fi
fi

echo ""

# ============================================================================
# Step 4: Run setup-pi.sh if first deployment
# ============================================================================

echo -e "${BLUE}[4/6]${NC} ${WRENCH} System setup..."

# Check if setup has been run (look for sentinel file)
if ssh pi@$HOST "[ -f ~/lemons/.setup-complete ]"; then
    echo -e "  ${GREEN}${CHECK} Pi already configured (skipping setup)${NC}"
else
    echo "  • Running first-time Pi setup..."
    echo "  ${YELLOW}  (This may take 5-10 minutes)${NC}"

    ssh pi@$HOST "cd ~/lemons && chmod +x scripts/setup-pi.sh && sudo ./scripts/setup-pi.sh"
    ssh pi@$HOST "touch ~/lemons/.setup-complete"

    echo -e "  ${GREEN}${CHECK} Pi configured${NC}"
    echo -e "  ${YELLOW}${WARN} Rebooting Pi...${NC}"

    ssh pi@$HOST "sudo reboot" || true

    echo "  • Waiting for Pi to come back online (60 seconds)..."
    sleep 60

    # Wait for SSH to be available again
    for i in {1..10}; do
        if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no pi@$HOST "echo test" &> /dev/null; then
            echo -e "  ${GREEN}${CHECK} Pi back online${NC}"
            break
        fi
        sleep 5
    done
fi

echo ""

# ============================================================================
# Step 5: Deploy applications
# ============================================================================

echo -e "${BLUE}[5/6]${NC} ${ROCKET} Deploying applications..."

ssh pi@$HOST "cd ~/lemons && export CAR_ID=$CAR_ID && chmod +x scripts/deploy.sh && ./scripts/deploy.sh all"

echo -e "  ${GREEN}${CHECK} Applications deployed${NC}"
echo ""

# ============================================================================
# Step 6: Verify deployment
# ============================================================================

echo -e "${BLUE}[6/6]${NC} ${WRENCH} Verifying deployment..."

# Give services a moment to start
sleep 3

# Check DRS service
echo -n "  • DRS service... "
if ssh pi@$HOST "systemctl is-active --quiet lemons@drs"; then
    echo -e "${GREEN}RUNNING ${CHECK}${NC}"
else
    echo -e "${RED}FAILED ${CROSS}${NC}"
    DEPLOY_FAILED=1
fi

# Check Telemetry service
echo -n "  • Telemetry service... "
if ssh pi@$HOST "systemctl is-active --quiet lemons@telemetry"; then
    echo -e "${GREEN}RUNNING ${CHECK}${NC}"
else
    echo -e "${RED}FAILED ${CROSS}${NC}"
    DEPLOY_FAILED=1
fi

# Health checks
echo -n "  • DRS health... "
if ssh pi@$HOST "curl -sf http://localhost:5001/healthz &> /dev/null"; then
    echo -e "${GREEN}HEALTHY ${CHECK}${NC}"
else
    echo -e "${YELLOW}DEGRADED ${WARN}${NC}"
fi

echo -n "  • Telemetry health... "
if ssh pi@$HOST "curl -sf http://localhost:5000/healthz &> /dev/null"; then
    echo -e "${GREEN}HEALTHY ${CHECK}${NC}"
else
    echo -e "${YELLOW}DEGRADED ${WARN}${NC}"
fi

echo ""

# ============================================================================
# Final status
# ============================================================================

if [ -n "$DEPLOY_FAILED" ]; then
    echo -e "${RED}╔════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          ❌ DEPLOYMENT FAILED              ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Check logs with:"
    echo "  ssh pi@$HOST journalctl -u lemons@drs -n 50"
    echo "  ssh pi@$HOST journalctl -u lemons@telemetry -n 50"
    exit 1
else
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║       ✅ DEPLOYMENT SUCCESSFUL!            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo "🎯 Quick access:"
    echo "  • Dashboard: http://$HOST:5000"
    echo "  • DRS API:   http://$HOST:5001/status"
    echo ""
    echo "📊 View logs:"
    echo "  make logs HOST=$HOST APP=drs"
    echo "  make logs HOST=$HOST APP=telemetry"
    echo ""
    echo "🏁 Car is ready to race!"
fi
