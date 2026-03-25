"""
DRS (Drag Reduction System) state machine.

States: IDLE → ACTIVE → IDLE, with FAULT for hardware errors.
Brake safety interlock: any brake press while ACTIVE forces immediate close.

This module receives its dependencies (gpio, servo, config) via constructor
injection. It does NOT import config.py.
"""


# States as strings (MicroPython has no enum stdlib)
IDLE = "idle"
ACTIVE = "active"
FAULT = "fault"


class DRS:
    """DRS controller with state machine and brake safety interlock."""

    def __init__(self, gpio, servo, drs_config, debounce_config):
        """
        Initialize DRS controller.

        Args:
            gpio: GPIOController instance (shared, from main.py).
            servo: Servo instance (owned by DRS).
            drs_config: Dict with open_angle, closed_angle, transition_time_ms.
            debounce_config: Dict with button_ms, brake_ms.
        """
        self._gpio = gpio
        self._servo = servo
        self._open_angle = drs_config["open_angle"]
        self._closed_angle = drs_config["closed_angle"]
        self._transition_ms = drs_config["transition_time_ms"]
        self._btn_debounce = debounce_config["button_ms"]
        self._brake_debounce = debounce_config["brake_ms"]

        self.state = IDLE

        # Register callbacks for edge-triggered events
        gpio.register_callback("DRS_BTN", self._on_button)
        gpio.register_callback("BRAKE_SWITCH", self._on_brake)

        # Safety: ensure servo starts closed
        try:
            self._servo.set_angle(self._closed_angle)
        except Exception as e:
            print("DRS: failed to close servo on init: {}".format(e))
            self.state = FAULT

    def poll(self):
        """
        Called every iteration of the main loop.

        Reads DRS button and brake switch with debouncing.
        State transitions happen via callbacks registered in __init__.
        """
        self._gpio.read_input("DRS_BTN", self._btn_debounce)
        self._gpio.read_input("BRAKE_SWITCH", self._brake_debounce)

    def get_state(self):
        """Return current state string for debugging."""
        return self.state

    def shutdown(self):
        """Force DRS closed. Called on exit."""
        self._close()

    def _on_button(self, pressed):
        """Handle DRS button press."""
        if not pressed:
            return

        if self.state == IDLE:
            self._open()
        elif self.state == ACTIVE:
            self._close()
        elif self.state == FAULT:
            # Attempt recovery on button press
            print("DRS: attempting recovery from FAULT")
            self._close()

    def _on_brake(self, pressed):
        """Brake safety interlock — immediately close DRS on any brake press."""
        if pressed and self.state == ACTIVE:
            print("DRS: brake pressed — closing")
            self._close()

    def _open(self):
        """Open wing (IDLE → ACTIVE)."""
        try:
            self._servo.set_angle(self._open_angle, self._transition_ms)
            self.state = ACTIVE
            print("DRS: ACTIVE ({}deg)".format(self._open_angle))
        except Exception as e:
            print("DRS: open failed: {}".format(e))
            self.state = FAULT

    def _close(self):
        """Close wing (any state → IDLE, or stay FAULT on error)."""
        was_fault = self.state == FAULT
        try:
            self._servo.set_angle(self._closed_angle, self._transition_ms)
            self.state = IDLE
            if was_fault:
                print("DRS: recovered from FAULT → IDLE")
            else:
                print("DRS: IDLE ({}deg)".format(self._closed_angle))
        except Exception as e:
            print("DRS: close failed: {}".format(e))
            self.state = FAULT
