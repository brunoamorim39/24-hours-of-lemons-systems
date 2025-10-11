#!/bin/bash
# Flash golden image to spare SD card
# Usage: ./flash-image.sh <device>

set -e

DEVICE=$1
IMAGE_DIR="golden-images"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$DEVICE" ]; then
    echo -e "${RED}❌ Error: Device not specified${NC}"
    echo "Usage: $0 /dev/sdX"
    echo ""
    echo "Find your SD card device:"
    echo "  Linux: lsblk"
    echo "  macOS: diskutil list"
    echo ""
    exit 1
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      💾 FLASH GOLDEN IMAGE                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Find latest golden image
if [ ! -d "$IMAGE_DIR" ]; then
    echo -e "${RED}❌ No golden images found${NC}"
    echo "Create one first with: make create-image"
    exit 1
fi

LATEST_IMAGE=$(ls -t $IMAGE_DIR/*.img* 2>/dev/null | head -1)

if [ -z "$LATEST_IMAGE" ]; then
    echo -e "${RED}❌ No .img files found in $IMAGE_DIR${NC}"
    exit 1
fi

echo "Image to flash: $LATEST_IMAGE"
echo "Target device:  $DEVICE"
echo ""

# Safety checks
echo -e "${YELLOW}⚠️  WARNING: This will ERASE all data on $DEVICE!${NC}"
echo ""

# Show device info
if command -v lsblk &> /dev/null; then
    echo "Device information:"
    lsblk $DEVICE 2>/dev/null || echo "  (unable to read device info)"
    echo ""
elif command -v diskutil &> /dev/null; then
    echo "Device information:"
    diskutil info $DEVICE 2>/dev/null || echo "  (unable to read device info)"
    echo ""
fi

read -p "Type 'yes' to continue: " confirm
[ "$confirm" = "yes" ] || exit 1

echo ""
echo "Unmounting device..."

# Unmount all partitions
if command -v umount &> /dev/null; then
    sudo umount ${DEVICE}* 2>/dev/null || true
elif command -v diskutil &> /dev/null; then
    sudo diskutil unmountDisk $DEVICE 2>/dev/null || true
fi

echo "Flashing image..."
echo "(This will take 5-15 minutes depending on SD card speed)"
echo ""

# Decompress if needed
if [[ "$LATEST_IMAGE" == *.gz ]]; then
    echo "Decompressing and flashing..."
    gunzip -c "$LATEST_IMAGE" | sudo dd of=$DEVICE bs=4M status=progress conv=fsync
else
    sudo dd if="$LATEST_IMAGE" of=$DEVICE bs=4M status=progress conv=fsync
fi

echo ""
echo "Syncing filesystem..."
sudo sync

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✅ IMAGE FLASHED SUCCESSFULLY        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Eject SD card safely"
echo "  2. Label SD card (e.g., 'LEMONS CAR1 SPARE 1')"
echo "  3. Test spare: Insert in Pi, power on, verify with:"
echo "     make verify-spare HOST=<pi-ip>"
echo ""
echo "💡 Tip: Create 2-3 spares for trackside peace of mind"
echo ""
