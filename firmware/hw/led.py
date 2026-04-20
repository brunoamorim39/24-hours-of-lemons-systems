"""
LED hardware abstraction.

Thin wrapper around GPIOController for a single on/off indicator LED.
App modules receive a Led instance via constructor injection; they never
touch GPIO pins directly.
"""

import time


class Led:
    """Simple on/off LED driven through GPIOController."""

    def __init__(self, gpio, pin_name):
        """
        Args:
            gpio: GPIOController instance (shared, from main.py).
            pin_name: Name of the LED output pin in GPIOController.
        """
        self._gpio = gpio
        self._pin = pin_name
        # Safety: LED off at construction
        self._gpio.write_output(self._pin, False)

    def on(self):
        """Drive LED on."""
        self._gpio.write_output(self._pin, True)

    def off(self):
        """Drive LED off."""
        self._gpio.write_output(self._pin, False)

    def flash(self, count, half_period_ms):
        """Blocking flash — intended for boot-time 'I'm alive' indicator.

        Blocks for roughly `count * 2 * half_period_ms` ms. Only safe to call
        before the main loop + watchdog are running.
        """
        for _ in range(count):
            self.on()
            time.sleep_ms(half_period_ms)
            self.off()
            time.sleep_ms(half_period_ms)
