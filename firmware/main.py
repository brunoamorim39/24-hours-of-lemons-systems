"""
Lemons DRS + PTT Controller — E46 325Ci
MicroPython on HiLetgo ESP32-DevKitC-32

This is the boot entry point and the ONLY file that imports config.
It wires config values into modules via constructor injection.
No application logic lives here — just init, wire, loop, shutdown.
"""

import time
from machine import WDT

from config import PINS, DRS as DRS_CONFIG, PTT as PTT_CONFIG, DEBOUNCE, WATCHDOG, LOOP
from hw import GPIOController, Servo, ServoActuator, PneumaticActuator
from drs import DRS
from ptt import PTT


def main():
    print("=" * 40)
    print("Lemons DRS+PTT — E46 325Ci")
    print("=" * 40)

    # --- Hardware init (config flows DOWN, never imported sideways) ---
    gpio = GPIOController(PINS)

    # --- DRS actuator (servo or pneumatic, selected by config) ---
    actuator_type = DRS_CONFIG["actuator_type"]

    if actuator_type == "servo":
        servo = Servo(
            pin=PINS["SERVO_PWM"],
            min_pulse_us=DRS_CONFIG["servo_min_pulse_us"],
            max_pulse_us=DRS_CONFIG["servo_max_pulse_us"],
            freq_hz=DRS_CONFIG["servo_freq_hz"],
            min_angle=DRS_CONFIG["servo_min_angle"],
            max_angle=DRS_CONFIG["servo_max_angle"],
        )
        actuator = ServoActuator(
            servo=servo,
            open_angle=DRS_CONFIG["open_angle"],
            closed_angle=DRS_CONFIG["closed_angle"],
            transition_ms=DRS_CONFIG["transition_time_ms"],
        )
    elif actuator_type == "pneumatic":
        actuator = PneumaticActuator(
            gpio=gpio,
            solenoid_pin_name="DRS_SOLENOID_OUT",
        )
    else:
        raise ValueError("Unknown actuator_type: {}".format(actuator_type))

    print("DRS actuator: {}".format(actuator_type))

    # --- Module init (each gets only the config it needs) ---
    drs = DRS(gpio, actuator, DEBOUNCE, DRS_CONFIG["max_active_ms"])
    ptt = PTT(gpio, PTT_CONFIG, DEBOUNCE)

    print("Hardware initialized. DRS={}, PTT=ready".format(drs.get_state()))

    # --- Hardware watchdog (resets ESP32 if main loop stalls) ---
    wdt = WDT(timeout=WATCHDOG["timeout_ms"])

    poll_ms = LOOP["poll_interval_ms"]

    # --- Main loop ---
    try:
        while True:
            drs.poll()
            ptt.poll()
            wdt.feed()
            time.sleep_ms(poll_ms)
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        print("Shutting down...")
        drs.shutdown()
        ptt.shutdown()
        print("Shutdown complete")


main()
