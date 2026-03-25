## Mission
- Help with **code**, **docs**, and **small tooling** for the E46 325Ci DRS + PTT controller.
- Prefer **practical fixes** over big refactors. We deploy trackside.

## Platform
- **ESP32** (HiLetgo ESP32-DevKitC-32), **MicroPython**.
- Firmware lives in `firmware/`. Uploaded via `mpremote`.
- No Flask, no systemd, no Docker, no Pi.

## Ground Rules
1. **No secrets in git.** Never add real credentials, tokens, or Wi-Fi keys.
2. **Keep hardware out of logic.** Use symbolic pins (e.g., `DRS_BTN`) in logic code. Pin numbers live only in `firmware/config.py`.
3. **Fail loud, fail safe.** If unsure, don't guess outputs that could move actuators unexpectedly.
4. **Small diffs.** Bite-sized PRs with clear titles and a 3–5 bullet summary.
5. **Docs or it didn't happen.** Update `README.md` / `docs/` when behavior or procedures change.

## Code Style
- MicroPython (ESP32). No type hints (not supported). Use docstrings.
- Structure:
  - `firmware/main.py` — boot entry, the ONLY file that imports `config.py`.
  - `firmware/drs.py`, `firmware/ptt.py` — application modules with state machines.
  - `firmware/hw/gpio.py`, `firmware/hw/servo.py` — hardware abstraction, app-agnostic.
  - `firmware/config.py` — single source of truth for all pins, angles, timeouts.
- **Zero magic numbers in logic code.** Every pin, angle, timeout, pulse width comes from config via constructor injection.
- **No defaults in constructors.** If config is missing a key, fail loudly.

## Safe Areas to Modify
- Extend `firmware/hw/` wrappers (GPIO, servo).
- Improve debounce, watchdog, error handling in firmware modules.
- Add new application modules (follow `drs.py`/`ptt.py` pattern).
- Update `firmware/config.py` tunables.

## Off-Limits Without Human OK
- Changing actuator default positions, servo directions, or safety interlocks.
- Any change that could move hardware on boot.
- Removing or weakening the brake safety interlock.

## Testing
- Testing is physical — bench test with serial monitor (`make esp32-monitor`).
- See README.md "Physical Test Procedures" for the full bench test checklist.
- No pytest (MicroPython code can't run under CPython).

## Commit / PR Format
- Title: `firmware/drs: add over-open pulse guard`
- Body:
  - What changed
  - Why it helps (race-day value)
  - Risk (low/med/high)
  - Rollback: "revert commit <sha>" or toggle config key

## Deployment
- Upload via USB: `make upload-firmware PORT=<port>`
- Reset: `make esp32-reset PORT=<port>`
- Monitor: `make esp32-monitor PORT=<port>`
