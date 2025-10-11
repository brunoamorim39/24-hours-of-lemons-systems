#!/bin/bash
# Pre-flight check script for Pi readiness
# Usage: ./check-pi.sh <host> [verify]

set -e

HOST=$1
MODE=${2:-check}  # check or verify

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHECK="✅"
CROSS="❌"
WARN="⚠️ "

if [ -z "$HOST" ]; then
    echo -e "${RED}${CROSS} Error: HOST not specified${NC}"
    echo "Usage: $0 <host>"
    exit 1
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      🔍 PI READINESS CHECK                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Target: ${GREEN}$HOST${NC}"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

# Helper function for checks
check() {
    local name=$1
    local command=$2
    local critical=${3:-yes}  # yes or no

    echo -n "  • $name... "

    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}PASS ${CHECK}${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        if [ "$critical" = "yes" ]; then
            echo -e "${RED}FAIL ${CROSS}${NC}"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
        else
            echo -e "${YELLOW}WARN ${WARN}${NC}"
            CHECKS_WARNED=$((CHECKS_WARNED + 1))
        fi
        return 1
    fi
}

# ============================================================================
# Network Checks
# ============================================================================

echo -e "${BLUE}Network Connectivity${NC}"

check "Ping test" "ping -c 1 -W 2 $HOST"

check "SSH connection" "ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no pi@$HOST 'echo test'"

check "Internet access" "ssh pi@$HOST 'ping -c 1 -W 2 8.8.8.8'" no

echo ""

# ============================================================================
# System Resources
# ============================================================================

echo -e "${BLUE}System Resources${NC}"

# Disk space
echo -n "  • Disk space... "
DISK_USAGE=$(ssh pi@$HOST "df / | tail -1 | awk '{print \$5}' | sed 's/%//'")
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}${DISK_USAGE}% used ${CHECK}${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}${DISK_USAGE}% used ${WARN}${NC}"
    CHECKS_WARNED=$((CHECKS_WARNED + 1))
fi

# Memory
echo -n "  • Free memory... "
FREE_MEM=$(ssh pi@$HOST "free -m | grep Mem | awk '{print \$7}'")
if [ "$FREE_MEM" -gt 100 ]; then
    echo -e "${GREEN}${FREE_MEM}MB free ${CHECK}${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}${FREE_MEM}MB free ${WARN}${NC}"
    CHECKS_WARNED=$((CHECKS_WARNED + 1))
fi

# Temperature
echo -n "  • CPU temperature... "
CPU_TEMP=$(ssh pi@$HOST "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0")
CPU_TEMP_C=$((CPU_TEMP / 1000))
if [ "$CPU_TEMP_C" -lt 70 ]; then
    echo -e "${GREEN}${CPU_TEMP_C}°C ${CHECK}${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
elif [ "$CPU_TEMP_C" -lt 80 ]; then
    echo -e "${YELLOW}${CPU_TEMP_C}°C ${WARN}${NC}"
    CHECKS_WARNED=$((CHECKS_WARNED + 1))
else
    echo -e "${RED}${CPU_TEMP_C}°C ${CROSS}${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo ""

# ============================================================================
# If verify mode, check services
# ============================================================================

if [ "$MODE" = "verify" ]; then
    echo -e "${BLUE}Service Status${NC}"

    check "DRS service running" "ssh pi@$HOST 'systemctl is-active --quiet lemons@drs'"

    check "Telemetry service running" "ssh pi@$HOST 'systemctl is-active --quiet lemons@telemetry'"

    check "DRS health check" "ssh pi@$HOST 'curl -sf http://localhost:5001/healthz'" no

    check "Telemetry health check" "ssh pi@$HOST 'curl -sf http://localhost:5000/healthz'" no

    echo ""
fi

# ============================================================================
# Final verdict
# ============================================================================

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNED))

echo "Results: ${GREEN}${CHECKS_PASSED} passed${NC} | ${RED}${CHECKS_FAILED} failed${NC} | ${YELLOW}${CHECKS_WARNED} warned${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ PI IS READY                    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    if [ $CHECKS_WARNED -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warnings detected but Pi should work${NC}"
    fi

    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          ❌ PI NOT READY                   ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Fix critical issues before deploying!"
    exit 1
fi
