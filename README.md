# 24 Hours of Lemons — E46 325Ci

DRS wing control + push-to-talk radio for our 24 Hours of Lemons E46 325Ci. ESP32 MicroPython firmware running on a HiLetgo ESP32-DevKitC-32.

## System Capabilities

| Capability | Status | Details |
|-----------|--------|---------|
| DRS actuator control | Working | Pneumatic (AirTAC 4V210-08 5/2 solenoid + MAL40×50 double-acting cylinder) installed; servo retained as `actuator_type="servo"` fallback |
| Brake safety interlock | Working | Optocoupler-isolated, immediate DRS close |
| Switched power rails | Working | Dash Controller Rocker + Air System Rocker — arm after engine start to avoid crank brownouts |
| PTT radio control | Working | Button keys Baofeng via 2N2222 transistor |
| PTT hold timeout | Working | 30s max transmit, auto-release safety |
| Hardware watchdog | Working | ESP32 WDT resets chip if firmware hangs |
| Spare button input | Wired | GPIO22 via XLR5, available for future use |
| Serial console debug | Working | `make esp32-monitor` for live output |
| DRS status LED | Working | GPIO26 → dash indicator (off=idle, solid=active, blink=fault, 3× flash on boot) |
| REST API / WiFi | Not yet | ESP32 has WiFi, could serve status later |
| Telemetry / OBD | Not yet | May add as separate concern later |
| Speed-based DRS lock | Not yet | No speed data on ESP32 currently |

### Safety Design

- **Brake override** — always closes DRS, highest priority
- **Default closed** — DRS starts closed, shuts down closed, faults to closed
- **Spool-spring fail-safe** — coil de-energize (power loss, brake, GPIO low) returns the valve spool to default; stored tank air routes to the cylinder's rod end and retracts the piston. Flap closes even with engine off, as long as there's tank pressure.
- **Two-key power arming** — Controller Rocker (ESP32) and Air System Rocker (valve coil + compressor signal) both gate 12V; no actuation possible until both are armed
- **Physical interlock** — solenoid coil lives on the switched accessory bus, so ESP32 cannot energize the valve while the air rocker is off
- **Hardware watchdog** — ESP32 resets if main loop stalls (10s timeout)
- **PTT timeout** — auto-release after 30s continuous transmit
- **Driver-visible status** — dash LED (off/solid/blink) reflects DRS state at a glance

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
# Expected (and the status LED flashes 3x on boot):
#   ========================================
#   Lemons DRS+PTT — E46 325Ci
#   ========================================
#   DRS actuator: pneumatic
#   DRS: IDLE
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
- Wire momentary button between GPIO4 and GND
- Press → `DRS: ACTIVE`
- Press again → `DRS: IDLE`

**3. Brake Safety Interlock**
- Activate DRS (press button)
- Short GPIO19 to GND (simulates optocoupler brake signal)
- Serial immediately shows `DRS: brake pressed — closing`

**4a. Servo Actuator Test** (when `actuator_type` is `"servo"` — legacy fallback)
- Connect servo: signal to GPIO18, power to 12V (via fuse), share GND with ESP32
- Press DRS button → servo moves to open angle
- Press again → servo returns to closed angle
- Adjust angles in `firmware/config.py` if needed

**4b. Pneumatic Actuator Test** (installed default — `actuator_type` is `"pneumatic"`)
- Flip Controller Rocker ON — ESP32 boots, status LED flashes 3x, serial banner prints `DRS actuator: pneumatic`, LED settles off (IDLE).
- Flip Air System Rocker ON — Viair compressor runs, tank gauge climbs to cut-out (~150 PSI), then cycles off. Regulator gauge shows set pressure (e.g. 40–50 PSI).
- Measure GPIO25 with multimeter (should read 0V at boot). Cylinder rod should be retracted (default state — air routed to rod end via valve's default position).
- Press DRS button → GPIO25 reads 3.3V (solenoid coil energized via MOSFET), audible valve click, cylinder extends (rod out), LED solid on.
- Press again → GPIO25 drops to 0V, spool returns, cylinder retracts (rod in), LED off.
- Brake interlock: activate DRS, short GPIO19 to GND → GPIO25 drops immediately, flap closes, LED off.
- Physical interlock: with tank charged, flip Air Rocker OFF only, press DRS button — GPIO25 still toggles but cylinder does not move (no 12V to coil, valve stays in default position).

**4c. Status LED Test**
- On boot: LED flashes 3x (~100 ms on / 100 ms off per cycle) then off
- Press DRS button: LED solid on (ACTIVE)
- Press again: LED off (IDLE)
- Force a FAULT (e.g. disconnect solenoid coil mid-cycle, or interrupt the actuator): LED blinks at ~1 Hz
- Press DRS button to recover from FAULT → `DRS: recovered from FAULT → IDLE` in serial, LED returns to off

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

All tunables live in `firmware/config.py` — the single source of truth.

**Switching DRS actuator type:**

```python
DRS = {
    "actuator_type": "pneumatic",  # installed default; set to "servo" for legacy fallback
    # ... servo tuning keys below are ignored when actuator_type is "pneumatic"
}
```

After editing: `make upload-firmware PORT=... && make esp32-reset PORT=...`

## Power-On / Shutdown

The car has two dash-mounted rocker switches that gate the 12V rails. Both stay OFF during crank to avoid brownouts.

**Power-on** (in this order):
1. Start engine, let idle stabilize.
2. Flip **Controller Rocker** ON — ESP32 boots, status LED flashes 3×, settles off (IDLE).
3. Flip **Air System Rocker** ON — compressor charges tank to cut-out pressure, self-cycles from then on.
4. System armed. DRS button operational. LED solid = flap open, off = flap closed.

**Shutdown** (in this order):
1. Flip **Air System Rocker** OFF — compressor stops; valve coil de-energizes; spool returns to default; cylinder retracts; flap closes.
2. Flip **Controller Rocker** OFF — ESP32 halts.
3. Engine off.
4. **Open the Viair tank drain petcock** (underside of tank) to vent residual tank pressure. Hold until tank gauge reads 0, then close.

## Circuit Diagrams

- [docs/e46-circuit.html](docs/e46-circuit.html) — electrical wiring, GPIO assignments, BOM.
- [docs/pneumatic-circuit.html](docs/pneumatic-circuit.html) — air plumbing (Viair 10000 → regulator → AirTAC 4V210-08 5/2 valve → MAL40×50 double-acting cylinder), with state-behavior explanation.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `esptool.py` can't connect | Hold BOOT button on ESP32 during flash |
| Port not found | Check USB cable (some are charge-only, no data) |
| Boot loop / repeated resets | Import error in firmware — check serial output |
| Servo jitters (fallback mode) | Check common ground between ESP32 and servo; check 12V supply |
| DRS won't activate | Verify DRS_BTN wiring (should short to GND on press); confirm both rockers are ON |
| Cylinder extends but retract is slow | Regulator pressure too low — retract force comes from supply pressure on the rod end, not a spring. Bump regulator up (within cylinder spec). Also verify EA exhaust port on valve is unobstructed. |
| GPIO25 toggles but cylinder doesn't move | Air Rocker likely off; or no air in tank; or regulator set to 0; or MOSFET/coil wiring broken |
| Flap stuck in last position after engine off | Tank emptied completely. Bleed via petcock anyway; on next run, verify tank charges before expecting flap control. |
| Status LED doesn't flash on boot | Check GPIO26 wiring, 220Ω resistor, LED polarity (flat side/short leg to GND) |
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
│       ├── servo.py            # PWM servo with angle limits (servo fallback)
│       ├── actuator.py         # ServoActuator + PneumaticActuator wrappers
│       └── led.py              # Dash-mount status LED (on/off/flash)
├── docs/
│   ├── e46-circuit.html        # Electrical wiring diagram + BOM
│   └── pneumatic-circuit.html  # Air plumbing diagram + pneumatic BOM
├── Makefile                    # ESP32 flash/upload/monitor commands
├── README.md
├── TRACKSIDE.md                # Printable pit-box reference
└── CLAUDE.md                   # Development guidelines
```

---

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines.
