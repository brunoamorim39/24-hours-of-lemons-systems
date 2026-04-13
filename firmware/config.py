"""
Single source of truth for all hardware and tuning parameters.

This is the ONLY file to edit when hardware changes. No other file
in the firmware contains pin numbers, angles, timeouts, or pulse widths.

main.py imports these dicts and passes them into modules via constructor
injection. No other module imports from this file.
"""

# --- Pin Assignments (ESP32 GPIO numbers) ---
# Change these when rewiring. No other file contains pin numbers.
PINS = {
    "SERVO_PWM": 18,           # PWM output to servo signal wire
    "DRS_SOLENOID_OUT": 25,    # GPIO for solenoid valve relay (pneumatic DRS)
    "BRAKE_SWITCH": 19,        # PC817 optocoupler output (active-low)
    "DRS_BTN": 4,              # XLR5 pin 2, momentary (active-low)
    "PTT_BTN": 21,             # XLR5 pin 3, momentary (active-low)
    "SPARE_BTN": 22,           # XLR5 pin 4, momentary (active-low)
    "PTT_OUT": 23,             # 1kΩ → 2N2222 base → Baofeng PTT
}

# --- DRS Actuator ---
DRS = {
    "actuator_type": "servo",      # "servo" or "pneumatic"
    "open_angle": 90,              # degrees — wing open position (operational setpoint)
    "closed_angle": 0,             # degrees — wing closed position (operational setpoint)
    "servo_min_angle": 0,          # degrees — servo mechanical min (maps to min_pulse)
    "servo_max_angle": 120,        # degrees — servo mechanical max (maps to max_pulse)
    "transition_time_ms": 500,     # ms — smooth transition duration (servo only)
    "servo_min_pulse_us": 900,     # μs — pulse width at servo_min_angle (servo only)
    "servo_max_pulse_us": 2100,    # μs — pulse width at servo_max_angle (servo only)
    "servo_freq_hz": 333,          # Hz — SV12T native update rate (servo only)
    "max_active_ms": 15000,        # ms — auto-close DRS after this long open (thermal safety)
}

# --- Input Debounce ---
DEBOUNCE = {
    "button_ms": 50,       # ms — DRS/PTT/spare button debounce
    "brake_ms": 20,        # ms — brake switch debounce (shorter for safety)
}

# --- PTT Radio ---
PTT = {
    "hold_timeout_ms": 30000,   # ms — max continuous transmit (safety cutoff)
}

# --- Watchdog ---
WATCHDOG = {
    "timeout_ms": 10000,   # ms — hardware WDT resets ESP32 if main loop stalls
}

# --- Polling ---
LOOP = {
    "poll_interval_ms": 10,  # ms — main loop sleep (~100Hz)
}
