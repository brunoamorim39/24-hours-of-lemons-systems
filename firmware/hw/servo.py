"""
Direct PWM servo driver for ESP32.

Application-agnostic — knows about angles and pulses, not about
wings or DRS. All parameters are required; no hidden defaults.

Safety: set_angle() validates the angle is within [min_angle, max_angle]
BEFORE writing to hardware. Out-of-range angles raise ValueError.
"""

import time
from machine import Pin, PWM


# Step interval for smooth transitions (matches 50Hz servo period)
_STEP_MS = 20


class Servo:
    """PWM servo controller with angle safety limits."""

    def __init__(self, pin, min_pulse_us, max_pulse_us, freq_hz, min_angle, max_angle):
        """
        Initialize servo on a GPIO pin.

        All parameters are required — values come from config via main.py.

        Args:
            pin: GPIO number for PWM output.
            min_pulse_us: Pulse width in μs at min_angle.
            max_pulse_us: Pulse width in μs at max_angle.
            freq_hz: PWM frequency (typically 50 for servos).
            min_angle: Minimum allowed angle in degrees.
            max_angle: Maximum allowed angle in degrees.
        """
        self._min_pulse_us = int(min_pulse_us)
        self._max_pulse_us = int(max_pulse_us)
        self._freq_hz = int(freq_hz)
        self._min_angle = int(min_angle)
        self._max_angle = int(max_angle)
        self._current_angle = None

        # Period in μs for duty cycle conversion
        self._period_us = 1000000 // self._freq_hz

        self._pwm = PWM(Pin(int(pin)), freq=self._freq_hz, duty_u16=0)

    def set_angle(self, angle, transition_time_ms=0):
        """
        Move servo to target angle.

        Args:
            angle: Target angle in degrees.
            transition_time_ms: Time to reach target (0 for instant).

        Raises:
            ValueError: If angle is outside [min_angle, max_angle].
        """
        angle = int(angle)
        transition_time_ms = int(transition_time_ms)

        if angle < self._min_angle or angle > self._max_angle:
            raise ValueError(
                "Angle {}deg outside safe range [{}deg, {}deg]".format(
                    angle, self._min_angle, self._max_angle
                )
            )

        if transition_time_ms > 0 and self._current_angle is not None:
            steps = max(1, transition_time_ms // _STEP_MS)
            start = self._current_angle
            delta = angle - start

            for i in range(1, steps):
                intermediate = start + delta * i // steps
                self._write_duty(intermediate)
                time.sleep_ms(_STEP_MS)

        self._write_duty(angle)
        self._current_angle = angle

    def get_angle(self):
        """Return current angle in degrees, or None if never set."""
        return self._current_angle

    def disable(self):
        """Stop sending PWM signal (servo goes limp)."""
        self._pwm.duty_u16(0)

    def _write_duty(self, angle):
        """Convert angle to duty cycle and write to PWM hardware."""
        # All integer math: angle → pulse_us → duty_u16
        angle_range = self._max_angle - self._min_angle
        pulse_range = self._max_pulse_us - self._min_pulse_us
        pulse_us = self._min_pulse_us + (angle - self._min_angle) * pulse_range // angle_range
        duty = pulse_us * 65535 // self._period_us
        self._pwm.duty_u16(duty)
