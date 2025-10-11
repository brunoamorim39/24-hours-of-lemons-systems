# 24 Hours of Lemons Systems

"Pro-motorsports tech on a ramen budget." This repo houses all Raspberry Pi apps and shared libraries for our 24 Hours of Lemons car(s): DRS control, telemetry, radios, dashboards, etc.

## Goals
- **One repo** → simpler deploys & hot-swaps at the track
- **Role-based** apps → a Pi runs one (or more) roles: `drs`, `telemetry`, `radio`
- **Car profiles** → swap chassis by changing config, not code
- **Fast pit ops** → single deploy script, templated systemd unit, health checks

---

## 🚨 TRACKSIDE EMERGENCY DEPLOYMENT

**Car computer failed? Here's your 2-minute recovery procedure:**

### Quick Swap (Golden Image Method - FASTEST)

```bash
# 1. Grab pre-imaged spare SD card from pit box
# 2. Power off Pi, swap SD card
# 3. Power on, wait 60 seconds for boot
# 4. Verify from your laptop:
make check-pi HOST=192.168.1.100
```

**Total time: ~2 minutes** ✅

### Remote Deploy (If No Spare SD Card)

```bash
# From your laptop (Pi must have fresh OS installed):
make deploy HOST=192.168.1.100 CAR=car1
```

**Total time: ~5-10 minutes** (first deploy) or ~2 minutes (code update only)

### Pre-Flight Check

```bash
# Verify Pi is ready before race:
make check-pi HOST=192.168.1.100
```

### View Logs

```bash
# If car is reporting issues:
make logs HOST=192.168.1.100 APP=drs
make logs HOST=192.168.1.100 APP=telemetry
```

### Common Errors

| Error | Fix |
|-------|-----|
| `Cannot reach HOST` | Check Pi power, network connection |
| `Cannot SSH` | Wait 60s for boot, verify WiFi config |
| `Service FAILED` | Check logs, verify config files |
| `DEGRADED health` | Non-critical, monitor but car is drivable |

**📋 Printable checklist:** See [TRACKSIDE.md](TRACKSIDE.md)

---

## Quick Start

### First-Time Pi Setup

1. **Prepare a Raspberry Pi** (Pi 4 or newer, with Raspberry Pi OS Bookworm)
   ```bash
   # On a fresh Raspberry Pi OS installation
   git clone https://github.com/your-org/24-hours-of-lemons-systems.git ~/lemons
   cd ~/lemons
   chmod +x scripts/*.sh
   ./scripts/setup-pi.sh
   sudo reboot
   ```

2. **Deploy Apps**
   ```bash
   cd ~/lemons
   export CAR_ID=car1  # or car2, car3, etc.
   ./scripts/deploy.sh all
   ```

3. **Verify Services**
   ```bash
   # Check DRS
   curl http://localhost:5001/status

   # Check Telemetry Dashboard
   # Open browser: http://<pi-ip-address>:5000
   ```

### Golden Image Strategy (Recommended for Trackside)

**The pro approach:** Pre-configure SD cards at home, keep spares in pit box.

#### At Home (One-Time Setup):

1. **Configure a Reference Pi**
   ```bash
   # On your laptop:
   make deploy HOST=192.168.1.100 CAR=car1

   # Verify everything works
   make check-pi HOST=192.168.1.100
   ```

2. **Create Golden Image**

   **Option A: From SD Card (Recommended)**
   ```bash
   # 1. Shut down Pi
   ssh pi@192.168.1.100 "sudo shutdown now"

   # 2. Remove SD card, insert into laptop

   # 3. Find SD card device
   lsblk  # Linux
   diskutil list  # macOS

   # 4. Create image
   sudo dd if=/dev/sdX of=golden-images/lemons-$(date +%Y%m%d).img bs=4M status=progress

   # 5. Compress (optional)
   gzip golden-images/lemons-$(date +%Y%m%d).img
   ```

   **Option B: Using Raspberry Pi Imager**
   - Download Raspberry Pi Imager
   - Use "Read" feature to backup SD card
   - Save as golden image

3. **Flash Spare SD Cards**
   ```bash
   # Insert blank SD card
   make flash-spare SD=/dev/sdX

   # Repeat for 2-3 spare cards
   ```

4. **Label & Store**
   - Label: "LEMONS CAR1 SPARE 1", "CAR1 SPARE 2", etc.
   - Store in waterproof case in pit box
   - Include metadata card with creation date & notes

#### At Track (Emergency Swap):

```bash
# 1. Grab spare SD card
# 2. Power off Pi, swap card
# 3. Power on, wait 60s
# 4. Verify: make check-pi HOST=192.168.1.100
# Total time: ~2 minutes
```

#### Updating Golden Images

**When to update:**
- After major code changes
- Before racing season
- After adding new features

**How to update:**
```bash
# Deploy latest code to one spare
make deploy HOST=192.168.1.100 CAR=car1

# Create new golden image
# (Follow "Create Golden Image" steps above)

# Re-flash all spares
```

---

## Architecture

### Apps

#### DRS (Drag Reduction System)
- **Purpose**: Control rear wing servo based on button input and brake safety interlock
- **State Machine**: `IDLE ↔ ACTIVE` (button toggles, brake forces IDLE)
- **Hardware**: GPIO button, brake switch, servo via PCA9685, status LED
- **API**: `http://localhost:5001/status` (for telemetry integration)
- **Config**: [config/roles/drs.yaml](config/roles/drs.yaml)

#### Telemetry
- **Purpose**: Collect OBD2 + custom metrics, display on web dashboard
- **Data Sources**:
  - OBD2: Speed, RPM, coolant temp, throttle, engine load
  - Custom: DRS status (via local API), future: radio, etc.
- **Dashboard**: `http://<pi-ip>:5000` (real-time WebSocket updates)
- **Config**: [config/roles/telemetry.yaml](config/roles/telemetry.yaml)

### Libraries

#### Hardware Abstraction Layer (`libs/hw/`)
- **gpio.py**: Button/switch inputs, LED outputs with debouncing
- **servo.py**: PCA9685 PWM servo control with safety limits
- **obd.py**: OBD-II interface via python-OBD

All HAL modules support `dry_run=True` for testing without hardware.

#### Utilities (`libs/util/`)
- **config.py**: YAML config loading and merging
- **logging.py**: Structured logging setup
- **watchdog.py**: Health monitoring and app restart

### Configuration

#### Role Configs (`config/roles/`)
Hardware-agnostic settings for each app:
- `drs.yaml`: Servo angles, debounce times, API port
- `telemetry.yaml`: OBD PIDs, update rates, dashboard port

#### Car Configs (`config/cars/`)
Hardware-specific pin mappings:
- `car1.yaml`: GPIO pins (BCM numbering), I2C addresses

**To add a new car**: Copy `car1.yaml` → `car2.yaml`, update pin numbers.

---

## Development

**IMPORTANT**: All development is done in Docker containers that match the Raspberry Pi environment exactly. This works on Windows, Mac, and Linux.

### Prerequisites

1. **Install Docker Desktop**
   - Windows/Mac: https://www.docker.com/products/docker-desktop
   - Linux: Install `docker` and `docker-compose` via package manager

2. **That's it.** No Python, no venv, no platform-specific bullshit.

### Quick Start

```bash
# Build development environment (first time only)
make build

# Start development shell
make dev

# Inside the container, you can run commands directly:
pytest
python -m apps.drs.main --dry-run
```

### Common Development Tasks

**Run Tests:**
```bash
make test           # All tests
make test-unit      # Unit tests only
make test-sim       # Simulation tests only
```

**Test Apps:**
```bash
make run-drs        # DRS app (http://localhost:5001)
make run-telemetry  # Telemetry dashboard (http://localhost:5000)
```

**Code Quality:**
```bash
make format         # Format with black
make lint           # Lint with ruff
```

### VS Code Integration (Optional)

If you use VS Code, it will detect the devcontainer config and ask:

> "Reopen in Container?"

Click "Reopen in Container" for a full IDE experience inside the Docker container with:
- Python intellisense
- Debugging
- Integrated terminal
- Extensions pre-installed

### Simulation Testing

The simulation framework allows testing DRS and telemetry apps with realistic track scenarios:

```bash
# Run full lap simulation
make test-sim

# Example output:
# ============================================================
# Starting 2-lap simulation: Laguna Seca
# ============================================================
#
# --- Lap 1/2 ---
#   [DRS] ACTIVATED @ 145.3 km/h
#   [DRS] DEACTIVATED @ 175.8 km/h
#   [DRS] ACTIVATED @ 152.1 km/h
#   Lap 1 complete: 89.45s
```

**Creating Custom Track Scenarios:**
1. Copy [tests/simulation/scenarios/laguna_seca.yaml](tests/simulation/scenarios/laguna_seca.yaml)
2. Define sectors with speed profiles, brake points, DRS zones
3. Run: `make test-sim`

### How It Works

- **Dockerfile**: Debian Bookworm (matches Pi OS Bookworm) + Python 3.11
- **docker-compose.yml**: Mounts your code, exposes ports
- **Makefile**: Simple commands that run everything in Docker
- **Your code**: Automatically synced into container

**No platform differences. No "works on my machine". Just code and deploy.**

### System Requirements

**Raspberry Pi:**
- Raspberry Pi 4 or newer
- **Raspberry Pi OS Bookworm** (Debian 12) - [Download here](https://www.raspberrypi.com/software/)
- Python 3.11 (included in Bookworm)

**Development Machine:**
- Docker Desktop (Windows/Mac) or Docker + docker-compose (Linux)
- That's it!

---

## Deployment

### Manual Deployment

```bash
# Deploy specific app
./scripts/deploy.sh drs
./scripts/deploy.sh telemetry

# Deploy all apps
./scripts/deploy.sh all

# Set car profile (default: car1)
export CAR_ID=car2
./scripts/deploy.sh all
```

### Systemd Service Management

```bash
# View logs
journalctl -u lemons@drs -f
journalctl -u lemons@telemetry -f

# Restart service
sudo systemctl restart lemons@drs

# Stop service
sudo systemctl stop lemons@drs

# Disable service
sudo systemctl disable lemons@drs
```

### Health Checks

```bash
# DRS
curl http://localhost:5001/healthz

# Telemetry
curl http://localhost:5000/healthz

# Example response:
# {"status": "healthy", "uptime": 1234.5, "recent_errors": []}
```

---

## Hardware Setup

### Required Components

- **Raspberry Pi 4** (or Pi 3B+)
- **PCA9685 PWM/Servo Driver** (for DRS servo control)
- **OBD-II to USB adapter** (ELM327-compatible)
- **GPIO buttons/switches** (DRS button, brake switch)
- **LEDs** (status indicators)
- **Servo** (for DRS wing actuation)

### Wiring

See `config/cars/car1.yaml` for pin mappings (BCM numbering):

```yaml
gpio:
  DRS_BTN: 17          # GPIO17 (Pin 11)
  BRAKE_SWITCH: 27     # GPIO27 (Pin 13)
  DRS_LED: 22          # GPIO22 (Pin 15)

i2c:
  PCA9685_ADDR: 0x40   # Default I2C address
```

**I2C Setup:**
```bash
# Enable I2C (already done by setup-pi.sh)
sudo raspi-config nonint do_i2c 0

# Verify I2C devices
i2cdetect -y 1
```

---

## Safety Notes

### DRS Safety Interlocks

- **Brake Override**: Brake switch immediately closes DRS (no delay)
- **Servo Limits**: Hard-coded min/max angles prevent over-rotation
- **Watchdog**: App restarts if main loop hangs
- **Default State**: DRS closed on startup/shutdown

### Testing Safety

Always test DRS in dry-run mode first:
```bash
python -m apps.drs.main --dry-run
```

Run full simulation tests before track deployment:
```bash
pytest tests/simulation/ -v
```

---

## Troubleshooting

### DRS Not Responding

```bash
# Check service status
sudo systemctl status lemons@drs

# Check logs
journalctl -u lemons@drs -n 50

# Test manually
python -m apps.drs.main --dry-run
```

### Telemetry Not Showing Data

```bash
# Check OBD connection
ls /dev/ttyUSB*  # Should show OBD adapter

# Test OBD manually
python3 -c "import obd; conn = obd.OBD(); print(conn.query(obd.commands.SPEED))"

# Check dashboard
curl http://localhost:5000/api/telemetry
```

### Servo Not Moving

```bash
# Check I2C connection
i2cdetect -y 1  # Should show 0x40

# Check servo power supply
# Servos need external 5V power (Pi GPIO can't provide enough current)
```

---

## Project Structure

```
24-hours-of-lemons-systems/
├── apps/                       # Role-based applications
│   ├── drs/                    # Drag Reduction System
│   │   ├── main.py             # State machine & main loop
│   │   └── api.py              # Flask API server
│   └── telemetry/              # Telemetry & dashboard
│       ├── main.py             # Data collection orchestrator
│       ├── dashboard.py        # Flask/WebSocket server
│       └── collectors/         # Data collectors (OBD, custom)
├── libs/
│   ├── hw/                     # Hardware abstraction layer
│   │   ├── gpio.py             # GPIO inputs/outputs
│   │   ├── servo.py            # Servo control
│   │   └── obd.py              # OBD-II interface
│   └── util/                   # Shared utilities
│       ├── config.py           # Config loading
│       ├── logging.py          # Logging setup
│       └── watchdog.py         # Health monitoring
├── config/
│   ├── roles/                  # App-specific configs
│   └── cars/                   # Car-specific pin mappings
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── simulation/             # Lap simulation tests
│       └── scenarios/          # Track definitions
├── scripts/
│   ├── deploy.sh               # Deployment script
│   └── setup-pi.sh             # Pi initial setup
├── systemd/
│   └── lemons@.service         # Templated systemd unit
└── web/
    └── telemetry/              # Dashboard web UI
        ├── index.html
        └── app.js
```

---

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and code style.

**Key Principles:**
- Keep hardware out of code (use config files)
- Fail loud, fail safe (especially for actuators)
- Small, testable changes
- Update docs when behavior changes

---

## License

MIT License - See [LICENSE](LICENSE) file.

---

## Credits

Built for 24 Hours of Lemons endurance racing. Because race cars should be fun, not expensive.

