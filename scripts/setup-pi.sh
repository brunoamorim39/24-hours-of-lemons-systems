#!/bin/bash
# One-time Raspberry Pi setup script
# Run this on a fresh Pi to install all dependencies

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}24 Hours of Lemons - Pi Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. Update system
echo -e "${GREEN}[1/7] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install Python and build tools
echo -e "${GREEN}[2/7] Installing Python and build tools...${NC}"
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    rsync

# 3. Install I2C and SPI tools
echo -e "${GREEN}[3/7] Installing I2C/SPI tools...${NC}"
sudo apt-get install -y \
    i2c-tools \
    python3-smbus \
    libgpiod2

# Enable I2C and SPI
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# 4. Install OBD tools (optional, for diagnostics)
echo -e "${GREEN}[4/7] Installing OBD tools...${NC}"
sudo apt-get install -y python3-serial

# 5. Install web server dependencies
echo -e "${GREEN}[5/7] Installing web server dependencies...${NC}"
sudo apt-get install -y nginx

# 6. Set up user permissions
echo -e "${GREEN}[6/7] Setting up user permissions...${NC}"
sudo usermod -a -G gpio,i2c,spi,dialout pi

# 7. Install Python packages globally (for systemd services)
echo -e "${GREEN}[7/7] Installing Python packages...${NC}"
pip3 install --user --upgrade pip setuptools wheel

# Done
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Reboot the Pi: sudo reboot"
echo "  2. Clone this repo: git clone <url> ~/lemons"
echo "  3. Set CAR_ID: export CAR_ID=car1"
echo "  4. Deploy: cd ~/lemons && ./scripts/deploy.sh all"
echo ""
