# 24 Hours of Lemons — E46 325Ci

DRS wing control + push-to-talk radio for our 24 Hours of Lemons E46 325Ci. ESP32 MicroPython firmware running on a HiLetgo ESP32-DevKitC-32.

## System Capabilities

| Capability | Status | Details |
|-----------|--------|---------|
| DRS servo control | Working | Direct GPIO PWM, 50Hz, smooth transitions |
| Brake safety interlock | Working | Optocoupler-isolated, immediate DRS close |
| PTT radio control | Working | Button keys Baofeng via 2N2222 transistor |
| PTT hold timeout | Working | 30s max transmit, auto-release safety |
| Hardware watchdog | Working | ESP32 WDT resets chip if firmware hangs |
| Spare button input | Wired | GPIO22 via XLR5, available for future use |
| Serial console debug | Working | `make esp32-monitor` for live output |
| DRS status LED | Not wired | No LED in current circuit |
| REST API / WiFi | Not yet | ESP32 has WiFi, could serve status later |
| Telemetry / OBD | Not yet | May add as separate concern later |
| Speed-based DRS lock | Not yet | No speed data on ESP32 currently |

### Safety Design

- **Brake override** — always closes DRS, highest priority
- **Default closed** — DRS starts closed, shuts down closed, faults to closed
- **Servo angle limits** — out-of-range rejected before hardware write
- **Hardware watchdog** — ESP32 resets if main loop stalls (10s timeout)
- **PTT timeout** — auto-release after 30s continuous transmit

---

## Prerequisites

Install on your laptop (these talk to USB hardware directly):

```bash
pip install esptool mpremote
```

Download MicroPython firmware for ESP32:
https://micropython.org/download/ESP32_GENERIC/

---

## First-Time Setup

```bash
# 1. Connect ESP32 via USB-C
# 2. Find the serial port
ls /dev/tty.usbserial-*     # macOS
ls /dev/ttyUSB*              # Linux

# 3. Flash MicroPython (hold BOOT button if flash fails to connect)
make flash-micropython FW=ESP32_GENERIC-20240602-v1.23.0.bin PORT=/dev/tty.usbserial-0001

# 4. Upload firmware
make upload-firmware PORT=/dev/tty.usbserial-0001

# 5. Verify boot
make esp32-monitor PORT=/dev/tty.usbserial-0001
# Expected:
#   ========================================
#   Lemons DRS+PTT — E46 325Ci
#   ========================================
#   DRS: IDLE (0deg)
#   Hardware initialized. DRS=idle, PTT=ready
```

## Updating Firmware

After editing any file in `firmware/`:

```bash
make upload-firmware PORT=/dev/tty.usbserial-0001
make esp32-reset PORT=/dev/tty.usbserial-0001
```

---

## Physical Test Procedures

Run these on the bench before installing in the car. Open serial monitor (`make esp32-monitor`) to see output.

**1. Boot Test** (no hardware connected)
- Power ESP32 via USB
- Serial shows init messages and `DRS=idle, PTT=ready`
- If you see repeated resets, check for import errors in serial output

**2. DRS Button Test**
- Wire momentary button between GPIO20 and GND
- Press → `DRS: ACTIVE (90deg)`
- Press again → `DRS: IDLE (0deg)`

**3. Brake Safety Interlock**
- Activate DRS (press button)
- Short GPIO19 to GND (simulates optocoupler brake signal)
- Serial immediately shows `DRS: brake pressed — closing`

**4. Servo Test**
- Connect servo: signal to GPIO18, power to 12V (via fuse), share GND with ESP32
- Press DRS button → servo moves to open angle
- Press again → servo returns to closed angle
- Adjust angles in `firmware/config.py` if needed

**5. PTT Test**
- Wire button between GPIO21 and GND
- Hold → measure GPIO23 with multimeter (should read 3.3V)
- Release → drops to 0V
- Or connect Baofeng and confirm radio keys/unkeys

**6. PTT Timeout Test**
- Hold PTT button >30 seconds
- Serial shows `PTT: hold timeout (30000ms) — forcing release`
- GPIO23 drops to 0V automatically

**7. Watchdog Test** (optional)
- Edit `firmware/main.py`, comment out `wdt.feed()`
- Upload and reset
- ESP32 resets itself after 10 seconds
- Restore `wdt.feed()` when done

---

## Configuration

All tunables live in `firmware/config.py` — the single source of truth:

```python
PINS = {
    "SERVO_PWM": 18,       # PWM output to servo
    "BRAKE_SWITCH": 19,    # Optocoupler output
    "DRS_BTN": 20,         # XLR5 pin 2
    "PTT_BTN": 21,         # XLR5 pin 3
    "SPARE_BTN": 22,       # XLR5 pin 4
    "PTT_OUT": 23,         # Transistor base drive
}
```

After editing: `make upload-firmware PORT=... && make esp32-reset PORT=...`

## Circuit Diagram

Open [docs/e46-circuit.html](docs/e46-circuit.html) in a browser for the full wiring diagram, GPIO assignments, and bill of materials.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `esptool.py` can't connect | Hold BOOT button on ESP32 during flash |
| Port not found | Check USB cable (some are charge-only, no data) |
| Boot loop / repeated resets | Import error in firmware — check serial output |
| Servo jitters | Check common ground between ESP32 and servo; check 12V supply |
| DRS won't activate | Verify DRS_BTN wiring (should short to GND on press) |
| PTT stuck transmitting | Check hold timeout in config; verify button wiring |
| `mpremote` can't connect | Close other serial monitors first (one connection at a time) |

---

## Project Structure

```
24-hours-of-lemons-systems/
├── firmware/                   # ESP32 MicroPython firmware
│   ├── main.py                 # Boot entry + main loop
│   ├── config.py               # Pin mappings + tunables (single source of truth)
│   ├── drs.py                  # DRS state machine (IDLE/ACTIVE/FAULT)
│   ├── ptt.py                  # PTT radio control
│   └── hw/                     # Hardware abstraction
│       ├── gpio.py             # Debounced GPIO with callbacks
│       └── servo.py            # PWM servo with angle limits
├── docs/
│   └── e46-circuit.html        # Circuit diagram + BOM
├── Makefile                    # ESP32 flash/upload/monitor commands
├── README.md
├── TRACKSIDE.md                # Printable pit-box reference
└── CLAUDE.md                   # Development guidelines
```

---

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines.
