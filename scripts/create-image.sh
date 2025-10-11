#!/bin/bash
# Create golden image from a configured Pi
# Usage: ./create-image.sh [host]

set -e

HOST=${1:-localhost}
IMAGE_DIR="golden-images"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="lemons-${TIMESTAMP}.img"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      💾 GOLDEN IMAGE CREATOR               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Create directory for images
mkdir -p "$IMAGE_DIR"

if [ "$HOST" = "localhost" ]; then
    echo "Creating image from local Pi..."
    echo ""
    echo -e "${YELLOW}⚠️  This script must run ON the Raspberry Pi${NC}"
    echo ""
    echo "Two options:"
    echo ""
    echo "1. Run this script ON the Pi:"
    echo "   ssh pi@<pi-ip>"
    echo "   cd ~/lemons"
    echo "   sudo ./scripts/create-image.sh"
    echo ""
    echo "2. Create image from SD card on your laptop:"
    echo "   • Shut down Pi and remove SD card"
    echo "   • Insert SD card into laptop"
    echo "   • Run: sudo dd if=/dev/sdX of=$IMAGE_DIR/$IMAGE_NAME bs=4M status=progress"
    echo "   • Replace /dev/sdX with your SD card device"
    echo ""
    echo "For safety, we recommend option 2 (image from SD card)."
    echo ""
    exit 1
else
    echo "Creating image from remote Pi: $HOST"
    echo ""
    echo -e "${YELLOW}⚠️  Remote imaging requires the Pi to be shut down${NC}"
    echo "This will:"
    echo "  1. Stop all services on $HOST"
    echo "  2. Shut down the Pi"
    echo "  3. You must then image the SD card manually"
    echo ""
    read -p "Continue? (yes/no): " confirm
    [ "$confirm" = "yes" ] || exit 1

    echo ""
    echo "Stopping services..."
    ssh pi@$HOST "sudo systemctl stop 'lemons@*'"

    echo "Shutting down Pi..."
    ssh pi@$HOST "sudo shutdown now"

    echo ""
    echo -e "${GREEN}✅ Pi is shutting down${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Wait for Pi to fully shut down (30 seconds)"
    echo "  2. Remove power from Pi"
    echo "  3. Remove SD card"
    echo "  4. Insert SD card into your laptop"
    echo "  5. Run imaging command:"
    echo ""
    echo "     Linux:"
    echo "       lsblk  # Find SD card device (e.g., /dev/sdb)"
    echo "       sudo dd if=/dev/sdX of=$IMAGE_DIR/$IMAGE_NAME bs=4M status=progress"
    echo ""
    echo "     macOS:"
    echo "       diskutil list  # Find SD card (e.g., /dev/disk2)"
    echo "       sudo dd if=/dev/rdiskX of=$IMAGE_DIR/$IMAGE_NAME bs=4m"
    echo ""
    echo "  6. Compress image (optional):"
    echo "       gzip $IMAGE_DIR/$IMAGE_NAME"
    echo ""
    echo "  7. Create metadata file:"
    echo "       echo 'Created: $TIMESTAMP' > $IMAGE_DIR/$IMAGE_NAME.txt"
    echo "       echo 'Car: <car_id>' >> $IMAGE_DIR/$IMAGE_NAME.txt"
    echo "       echo 'Notes: <any notes>' >> $IMAGE_DIR/$IMAGE_NAME.txt"
    echo ""
fi
