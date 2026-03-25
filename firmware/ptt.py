"""
PTT (Push-to-Talk) radio controller.

Button press drives a transistor output to key the Baofeng radio.
Safety: hold timeout forces release after a configurable duration
to prevent stuck transmit if the button jams.

This module receives its dependencies (gpio, config) via constructor
injection. It does NOT import config.py.
"""

import time


class PTT:
    """PTT radio controller with hold timeout safety."""

    def __init__(self, gpio, ptt_config, debounce_config):
        """
        Initialize PTT controller.

        Args:
            gpio: GPIOController instance (shared, from main.py).
            ptt_config: Dict with hold_timeout_ms.
            debounce_config: Dict with button_ms.
        """
        self._gpio = gpio
        self._hold_timeout_ms = ptt_config["hold_timeout_ms"]
        self._btn_debounce = debounce_config["button_ms"]

        self._transmitting = False
        self._tx_start = 0  # ticks_ms when transmit began

        gpio.register_callback("PTT_BTN", self._on_button)

        # Safety: ensure PTT is off at init
        gpio.write_output("PTT_OUT", False)

    def poll(self):
        """
        Called every iteration of the main loop.

        Reads PTT button with debouncing and enforces hold timeout.
        """
        self._gpio.read_input("PTT_BTN", self._btn_debounce)

        # Hold timeout safety: force release if transmitting too long
        if self._transmitting:
            elapsed = time.ticks_diff(time.ticks_ms(), self._tx_start)
            if elapsed >= self._hold_timeout_ms:
                print("PTT: hold timeout ({}ms) — forcing release".format(
                    self._hold_timeout_ms
                ))
                self._release()

    def shutdown(self):
        """Force PTT off. Called on exit."""
        self._release()

    def _on_button(self, pressed):
        """Handle PTT button state change."""
        if pressed and not self._transmitting:
            self._key()
        elif not pressed and self._transmitting:
            self._release()

    def _key(self):
        """Key the radio (start transmitting)."""
        self._gpio.write_output("PTT_OUT", True)
        self._transmitting = True
        self._tx_start = time.ticks_ms()
        print("PTT: keyed")

    def _release(self):
        """Unkey the radio (stop transmitting)."""
        self._gpio.write_output("PTT_OUT", False)
        self._transmitting = False
        print("PTT: released")
