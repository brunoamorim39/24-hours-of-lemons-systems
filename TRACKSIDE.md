# 🏁 TRACKSIDE QUICK REFERENCE

**Print this page and keep in pit box!**

---

## PRE-RACE CHECKLIST

- [ ] Spare SD cards in waterproof case (labeled)
- [ ] Laptop charged + power adapter
- [ ] Laptop connected to pit WiFi network
- [ ] Know Pi IP address: `__________________`
- [ ] Verify systems before qualifying:
  ```
  make check-pi HOST=<ip>
  ```

---

## EMERGENCY: PI FAILED

### OPTION 1: Spare SD Card Swap (2 min)

**Car is coming in NOW:**

1. ⚡ Grab spare SD card from pit box
2. ⚡ Power off Pi in car
3. ⚡ Swap SD card
4. ⚡ Power on Pi
5. ⏱️  Wait 60 seconds for boot
6. ✅ Verify: `make check-pi HOST=<ip>`

**SEND CAR BACK OUT!**

---

### OPTION 2: Remote Deploy (5-10 min)

**If no spare SD card available:**

```bash
# From your laptop:
make deploy HOST=<pi-ip> CAR=car1
```

Wait for "DEPLOYMENT SUCCESSFUL"

---

## CODE UPDATE (Between Sessions)

**New code to deploy:**

```bash
make deploy HOST=<pi-ip> CAR=car1
```

---

## TROUBLESHOOTING

### Cannot Reach Pi

```bash
# 1. Check power to Pi
# 2. Verify network:
ping <pi-ip>

# 3. Check WiFi antenna connection
```

### Service Not Running

```bash
# Check logs:
make logs HOST=<pi-ip> APP=drs
make logs HOST=<pi-ip> APP=telemetry

# Restart service (from laptop):
ssh pi@<pi-ip> "sudo systemctl restart lemons@drs"
```

### Dashboard Not Accessible

```bash
# 1. Verify telemetry service:
make check-pi HOST=<pi-ip>

# 2. Check network:
curl http://<pi-ip>:5000/healthz

# 3. Check firewall (on Pi):
ssh pi@<pi-ip> "sudo ufw status"
```

### DRS Not Responding

```bash
# 1. Check DRS service:
ssh pi@<pi-ip> "sudo systemctl status lemons@drs"

# 2. Check servo power supply (external 5V)
# 3. Check GPIO connections
# 4. Test manually:
curl http://<pi-ip>:5001/status
```

---

## QUICK COMMANDS

| Task | Command |
|------|---------|
| Check Pi health | `make check-pi HOST=<ip>` |
| Deploy all | `make deploy HOST=<ip> CAR=car1` |
| View DRS logs | `make logs HOST=<ip> APP=drs` |
| View telemetry logs | `make logs HOST=<ip> APP=telemetry` |
| SSH to Pi | `ssh pi@<ip>` |
| Restart DRS | `ssh pi@<ip> "sudo systemctl restart lemons@drs"` |
| Restart telemetry | `ssh pi@<ip> "sudo systemctl restart lemons@telemetry"` |

---

## DASHBOARD URLS

- **Telemetry Dashboard:** `http://<pi-ip>:5000`
- **DRS API Status:** `http://<pi-ip>:5001/status`
- **Health Checks:** `http://<pi-ip>:5000/healthz`, `http://<pi-ip>:5001/healthz`

---

## PI INFO

**Default Credentials:**
- Username: `pi`
- Password: `raspberry` (or as configured)

**Our Pi Hostnames:**
- Car 1: `lemons-car1.local` or `192.168.1.___`
- Car 2: `lemons-car2.local` or `192.168.1.___`

---

## CONTACT INFO (IF STUCK)

**Team Lead:** `______________________`

**Phone:** `______________________`

---

## GOLDEN IMAGE INFO

**Spare SD Cards:**
- Location: `______________________`
- Last Updated: `______________________`
- Version: `______________________`

**To Create New Golden Image (at home):**

1. Configure one Pi perfectly
2. Run: `make create-image`
3. Flash to spares: `make flash-spare SD=/dev/sdX`
4. Label and store in pit box

---

## RACE DAY NOTES

Use this space for track-specific info:

```
Network SSID: _______________________
Network Pass: _______________________

Pi IP Address: _______________________

Special Config: _______________________
_______________________________________
_______________________________________

Issues Encountered: _______________________
_______________________________________
_______________________________________
```

---

**Last Updated:** `________________` **By:** `________________`

**🏁 Remember: Keep calm, follow checklist, send it! 🏁**
