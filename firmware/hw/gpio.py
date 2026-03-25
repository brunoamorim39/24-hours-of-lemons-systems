"""
Generic GPIO controller with debouncing and callbacks.

Application-agnostic — knows nothing about DRS, PTT, or any application
concept. Provides debounced digital I/O primitives over symbolic pin names.

Pin direction is inferred by naming convention:
  - Names containing "OUT" → output (initial LOW)
  - Everything else → input with internal pull-up (active-low)
"""

import time
from machine import Pin


class GPIOController:
    """Debounced GPIO inputs and outputs with symbolic naming."""

    def __init__(self, pin_config):
        """
        Initialize GPIO controller.

        Args:
            pin_config: Dict mapping symbolic names to GPIO numbers.
                        e.g. {"DRS_BTN": 20, "PTT_OUT": 23}
                        Direction is inferred from the name.
        """
        self._pins = {}        # name -> Pin object
        self._state = {}       # name -> bool (current debounced state)
        self._last_read = {}   # name -> ticks_ms of last read
        self._callbacks = {}   # name -> list of callables

        for name, num in pin_config.items():
            if "OUT" in name.upper():
                self._pins[name] = Pin(num, Pin.OUT, value=0)
                self._state[name] = False
            else:
                self._pins[name] = Pin(num, Pin.IN, Pin.PULL_UP)
                self._state[name] = False
                self._last_read[name] = time.ticks_ms()

    def read_input(self, name, debounce_ms):
        """
        Read debounced input state.

        Args:
            name: Symbolic pin name from config.
            debounce_ms: Minimum ms between reads.

        Returns:
            True if input is active (button pressed / switch closed).

        Raises:
            KeyError: If name is not a configured pin.
        """
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, self._last_read[name])

        if elapsed < debounce_ms:
            return self._state[name]

        # Active-low: pressed/closed = pin reads 0
        value = not self._pins[name].value()

        prev = self._state[name]
        if value != prev:
            self._state[name] = value
            self._fire_callbacks(name, value)

        self._last_read[name] = now
        return value

    def write_output(self, name, value):
        """
        Set output pin HIGH or LOW.

        Args:
            name: Symbolic pin name from config.
            value: True for HIGH, False for LOW.

        Raises:
            KeyError: If name is not a configured pin.
        """
        self._pins[name].value(1 if value else 0)
        self._state[name] = value

    def register_callback(self, name, fn):
        """
        Register a callback for input state changes.

        The callback receives one argument: the new boolean state
        (True = pressed/active, False = released/inactive).

        Args:
            name: Symbolic pin name from config.
            fn: Callable(bool) invoked on state change.
        """
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(fn)

    def _fire_callbacks(self, name, value):
        """Invoke all registered callbacks for a pin."""
        for fn in self._callbacks.get(name, []):
            try:
                fn(value)
            except Exception as e:
                print("GPIO callback error [{}]: {}".format(name, e))
