# TRACKSIDE QUICK REFERENCE

**Print this page and keep in pit box!**

---

## PRE-RACE CHECKLIST

- [ ] Laptop charged + USB-C cable for ESP32
- [ ] Engine running before flipping dash rockers (avoids crank brownout)
- [ ] Flip **Controller Rocker** ON → status LED flashes 3x, then off (IDLE)
- [ ] Flip **Air System Rocker** ON → compressor spools, tank gauge climbs, regulator holds set pressure
- [ ] Verify serial output: `DRS actuator: pneumatic` (or `servo` if running fallback)
- [ ] DRS button test: press → flap opens + LED solid on, press → flap closes + LED off
- [ ] Brake interlock test: activate DRS → tap brake → flap closes immediately + LED off
- [ ] PTT test: hold button → radio keys, release → radio unkeys
- [ ] Shutdown sequence briefed: Air Rocker OFF → Controller Rocker OFF → engine off → open Viair tank drain petcock until gauge reads 0, then close

---

## EMERGENCY: ESP32 NOT RESPONDING

### Re-Upload Firmware (2 min)

```bash
# 1. Connect laptop to ESP32 via USB-C
# 2. Upload firmware:
make upload-firmware PORT=/dev/tty.usbserial-0001

# 3. Reset:
make esp32-reset PORT=/dev/tty.usbserial-0001
```

### Check Serial Output

```bash
make esp32-monitor PORT=/dev/tty.usbserial-0001
```

Look for error messages. Common issues:
- Boot loop = import error in firmware code
- No output = wrong serial port or bad USB cable

---

## TROUBLESHOOTING

### DRS Not Responding

1. **Both rockers ON?** Controller Rocker powers ESP32; Air System Rocker powers compressor + valve coil. Either off = no actuation.
2. Check status LED — no flash on boot means ESP32 isn't getting power (Controller Rocker, fuse, buck converter, USB cable).
3. Check serial output: `make esp32-monitor`
4. Check GPIO4 button wiring (should short to GND on press)
5. Re-upload firmware if needed

### Flap Opens But Retracts Slowly

1. Regulator pressure too low — retract force comes from regulator pressure on the cylinder's rod end (no spring). Bump it up (within cylinder spec).
2. Check the valve's EA exhaust port (the one that vents the cap end on retract) — if it's muffled, plugged, or pointed at a wall, it'll throttle the retract.
3. Kinked or pinched 8mm tubing between valve B port and cylinder rod end?

### Cylinder Doesn't Move At All

1. Is the Air Rocker ON? (obvious but first)
2. Tank pressure: gauge reading? Compressor cycling?
3. Regulator gauge reading? Try bumping it up.
4. Measure GPIO25 when DRS button pressed — should read 3.3V. If 0V, button/firmware issue. If 3.3V but no cylinder movement, MOSFET / coil / 12V-to-coil wiring broken.

### Status LED Dead

1. Check GPIO26 with multimeter (~3.3V on ACTIVE, 0V on IDLE, toggling on FAULT)
2. Check 220Ω resistor inline
3. Check LED polarity — flat side / short leg to GND

### PTT Not Working

1. Check GPIO21 button wiring
2. Check GPIO23 → 1kΩ → 2N2222 transistor wiring
3. Check Baofeng radio power and connection
4. Check serial output for PTT messages

### Servo Jitters or No Movement (legacy fallback mode)

1. Confirm `actuator_type` is `"servo"` in `firmware/config.py`
2. Check common ground between ESP32 and servo
3. Check 12V supply to servo (through 5A fuse)
4. Check GPIO18 signal wire to servo

---

## QUICK COMMANDS

| Task | Command |
|------|---------|
| Upload firmware | `make upload-firmware PORT=<port>` |
| Serial monitor | `make esp32-monitor PORT=<port>` |
| Reset ESP32 | `make esp32-reset PORT=<port>` |

---

## CIRCUIT DIAGRAMS

- `docs/e46-circuit.html` — electrical wiring, GPIO pins, rockers, MOSFET, LED, BOM
- `docs/pneumatic-circuit.html` — air plumbing: Viair 10000 (compressor + tank) → regulator → 5/2 valve (A/B) → MAL40×50 double-acting cylinder

---

## RACE DAY NOTES

```
ESP32 Serial Port: _______________________

DRS Actuator Type: ______ (pneumatic installed; servo fallback)
Regulator Set Pressure: _______ PSI
Tank Cut-In / Cut-Out: _______ / _______ PSI

Issues Encountered: _______________________
_______________________________________
_______________________________________
```

---

**Last Updated:** `________________` **By:** `________________`
