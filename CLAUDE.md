## Mission
- Help with **code**, **docs**, **tests**, and **small tooling**.
- Prefer **practical fixes** over big refactors. We deploy trackside.

## Ground Rules
1. **No secrets in git.** Never add real credentials, tokens, or Wi-Fi keys.
2. **Keep hardware out of code.** Use symbolic pins (e.g., `DRS_BTN`) and map them in `config/cars/*.yaml`.
3. **Fail loud, fail safe.** If unsure, don’t guess outputs that could move actuators unexpectedly.
4. **Small diffs.** Bite-sized PRs with clear titles and a 3–5 bullet summary.
5. **Docs or it didn’t happen.** Update `README.md` / `docs/` when behavior or procedures change.

## Code Style
- Python 3.11+ (matches Pi OS Bookworm), `black`/`ruff`. Use type hints & docstrings.
- Structure:
  - Apps live in `apps/<role>/main.py` with a small **state machine**.
  - Hardware in `libs/hw/*` (GPIO, PCA9685, ADC, OBD) with thin, testable wrappers.
  - Utilities in `libs/util/*` (logging, debounce, watchdog, web).
- No hard-coded timeouts/angles: put tunables in `config/roles/*.yaml`.

## Safe Areas to Modify
- Add/extend **HAL** wrappers (PCA9685 servo, MCP3008 ADC, python-OBD).
- Improve **debounce**, **logging**, **watchdog**, and **error handling**.
- Build **Flask/WebSocket** dashboards and `/healthz` endpoints.
- Write **tests** for state machines (mock HAL).

## Off-Limits Without Human OK
- Changing actuator default positions, servo directions, or safety interlocks.
- Modifying systemd unit behavior (`lemons@.service`) beyond args.
- Any change that could move hardware on boot.

## Testing Expectations
- Unit tests pass locally (`pytest`).
- Simulated runs don’t raise on missing hardware (HAL can be mocked).
- `apps/<role>/main.py --dry-run` should start without GPIO/I²C.

## Commit / PR Format
- Title: `apps/drs: add over-open pulse guard`
- Body:
  - What changed
  - Why it helps (race-day value)
  - Risk (low/med/high)
  - Rollback: “revert commit <sha>” or toggle config key

## Deployment Notes
- Don’t embed deploy-specific hostnames in code.
- Keep `./scripts/deploy.sh` idempotent and simple.
- Assume the Pi runs as `pi` with systemd templated service:
