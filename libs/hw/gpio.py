"""GPIO controller for buttons, switches, and LEDs with debouncing."""

import time
from typing import Callable, Dict, Optional


class GPIOController:
    """Abstraction for GPIO inputs (buttons/switches) and outputs (LEDs)."""

    def __init__(self, pin_config: Dict[str, int], dry_run: bool = False):
        """
        Initialize GPIO controller.

        Args:
            pin_config: Dict mapping symbolic names to BCM pin numbers
                       e.g., {"DRS_BTN": 17, "BRAKE_SWITCH": 27, "DRS_LED": 22}
            dry_run: If True, mock GPIO without actual hardware
        """
        self.pin_config = pin_config
        self.dry_run = dry_run
        self._state: Dict[str, bool] = {}
        self._last_read: Dict[str, float] = {}
        self._callbacks: Dict[str, list] = {}

        if not dry_run:
            try:
                import RPi.GPIO as GPIO

                self.GPIO = GPIO
                self.GPIO.setmode(GPIO.BCM)
                self.GPIO.setwarnings(False)
            except ImportError:
                print("Warning: RPi.GPIO not available, forcing dry-run mode")
                self.dry_run = True

        self._setup_pins()

    def _setup_pins(self):
        """Configure pins as inputs or outputs based on naming convention."""
        for name, pin in self.pin_config.items():
            # Outputs: LED, RELAY, etc.
            # Inputs: BTN, BUTTON, SWITCH, SENSOR, etc.
            if any(x in name.upper() for x in ["LED", "RELAY", "OUT"]):
                if not self.dry_run:
                    self.GPIO.setup(pin, self.GPIO.OUT)
                    self.GPIO.output(pin, self.GPIO.LOW)
                self._state[name] = False
            else:
                if not self.dry_run:
                    # Use pull-up for buttons/switches (active-low)
                    self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
                self._state[name] = False
                self._last_read[name] = time.time()

    def read_input(self, name: str, debounce_ms: int = 50) -> bool:
        """
        Read debounced input from button or switch.

        Args:
            name: Symbolic name from pin_config
            debounce_ms: Debounce time in milliseconds

        Returns:
            True if input is active (button pressed, switch closed)
        """
        if name not in self.pin_config:
            raise ValueError(f"Unknown pin: {name}")

        now = time.time()
        debounce_s = debounce_ms / 1000.0

        # Debouncing: only read if enough time has passed
        if now - self._last_read.get(name, 0) < debounce_s:
            return self._state.get(name, False)

        if self.dry_run:
            # In dry-run, state can be set externally for testing
            value = self._state.get(name, False)
        else:
            # Active-low logic: pressed/closed = LOW = 0
            pin = self.pin_config[name]
            value = not self.GPIO.input(pin)

        # Detect state change
        prev_state = self._state.get(name, False)
        if value != prev_state:
            self._state[name] = value
            self._trigger_callbacks(name, value)

        self._last_read[name] = now
        return value

    def write_output(self, name: str, value: bool):
        """
        Set output pin (LED, relay, etc.).

        Args:
            name: Symbolic name from pin_config
            value: True for HIGH, False for LOW
        """
        if name not in self.pin_config:
            raise ValueError(f"Unknown pin: {name}")

        self._state[name] = value

        if self.dry_run:
            print(f"[GPIO DRY-RUN] {name} = {'HIGH' if value else 'LOW'}")
        else:
            pin = self.pin_config[name]
            self.GPIO.output(pin, self.GPIO.HIGH if value else self.GPIO.LOW)

    def register_callback(self, name: str, callback: Callable[[bool], None]):
        """
        Register callback for input state changes.

        Args:
            name: Symbolic name from pin_config
            callback: Function called with new state when input changes
        """
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

    def _trigger_callbacks(self, name: str, value: bool):
        """Trigger all callbacks for a pin."""
        for callback in self._callbacks.get(name, []):
            try:
                callback(value)
            except Exception as e:
                print(f"Error in callback for {name}: {e}")

    def set_mock_input(self, name: str, value: bool):
        """
        Set mock input state for testing (dry-run mode only).

        Args:
            name: Symbolic name from pin_config
            value: Mock state (True = pressed/closed)
        """
        if not self.dry_run:
            raise RuntimeError("set_mock_input only available in dry-run mode")
        self._state[name] = value
        self._trigger_callbacks(name, value)

    def cleanup(self):
        """Clean up GPIO resources."""
        if not self.dry_run:
            self.GPIO.cleanup()
