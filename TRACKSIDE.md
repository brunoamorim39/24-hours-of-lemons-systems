# TRACKSIDE QUICK REFERENCE

**Print this page and keep in pit box!**

---

## PRE-RACE CHECKLIST

- [ ] Laptop charged + USB-C cable for ESP32
- [ ] ESP32 powered and running (verify serial output)
- [ ] DRS button test: press → wing opens, press → wing closes
- [ ] Brake interlock test: activate DRS → press brake → wing closes
- [ ] PTT test: hold button → radio keys, release → radio unkeys
- [ ] Actuator power: 12V through fuse, common ground with ESP32
- [ ] Verify actuator type in serial: `DRS actuator: servo` or `DRS actuator: pneumatic`

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

1. Check ESP32 power (USB or 5V from buck converter)
2. Check serial output: `make esp32-monitor`
3. Check actuator power (12V through fuse)
4. Check GPIO4 button wiring (should short to GND)
5. Re-upload firmware if needed

### PTT Not Working

1. Check GPIO21 button wiring
2. Check GPIO23 → 1kΩ → 2N2222 transistor wiring
3. Check Baofeng radio power and connection
4. Check serial output for PTT messages

### Servo Jitters or No Movement (servo mode)

1. Check common ground between ESP32 and servo
2. Check 12V supply to servo (through 5A fuse)
3. Check GPIO18 signal wire to servo

### Solenoid Not Firing (pneumatic mode)

1. Check GPIO25 output with multimeter (3.3V when DRS active)
2. Check relay/MOSFET wiring from GPIO25 to solenoid valve
3. Check 12V supply to solenoid valve
4. Check air pressure (compressor running, tank not empty)

---

## QUICK COMMANDS

| Task | Command |
|------|---------|
| Upload firmware | `make upload-firmware PORT=<port>` |
| Serial monitor | `make esp32-monitor PORT=<port>` |
| Reset ESP32 | `make esp32-reset PORT=<port>` |

---

## CIRCUIT DIAGRAM

Open `docs/e46-circuit.html` in any browser for full wiring reference.

---

## RACE DAY NOTES

```
ESP32 Serial Port: _______________________

DRS Actuator Type: ______ (servo / pneumatic)
DRS Open Angle: _______ Closed Angle: _______ (servo only)

Issues Encountered: _______________________
_______________________________________
_______________________________________
```

---

**Last Updated:** `________________` **By:** `________________`
