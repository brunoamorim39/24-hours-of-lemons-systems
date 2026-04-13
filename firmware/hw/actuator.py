"""
Actuator abstraction for DRS wing control.

Two implementations with the same interface:
- ServoActuator: wraps a Servo for angular position control.
- PneumaticActuator: drives a solenoid valve via GPIO for binary open/close.

Modules that use an actuator call open(), close(), disable() and never
need to know which type is behind the interface.
"""


class ServoActuator:
    """Actuator backed by a PWM servo motor.

    Holds PWM continuously in both open and closed positions. The SV12T
    (and digital servos generally) will not release torque via signal
    manipulation — they treat signal loss as 'hold last position.'
    True release requires cutting 12V power via external switching.
    """

    def __init__(self, servo, open_angle, closed_angle, transition_ms):
        """
        Args:
            servo: Servo instance (from hw.servo).
            open_angle: Angle in degrees for the open position.
            closed_angle: Angle in degrees for the closed position.
            transition_ms: Smooth transition duration in milliseconds.
        """
        self._servo = servo
        self._open_angle = open_angle
        self._closed_angle = closed_angle
        self._transition_ms = transition_ms

    def open(self):
        """Move servo to open angle."""
        self._servo.set_angle(self._open_angle, self._transition_ms)

    def close(self):
        """Move servo to closed angle."""
        self._servo.set_angle(self._closed_angle, self._transition_ms)

    def disable(self):
        """Stop PWM signal (shutdown only — servo may still hold position)."""
        self._servo.disable()


class PneumaticActuator:
    """Actuator backed by a solenoid valve driven via GPIO."""

    def __init__(self, gpio, solenoid_pin_name):
        """
        Args:
            gpio: GPIOController instance (shared, from main.py).
            solenoid_pin_name: Name of the solenoid output pin in GPIOController.
        """
        self._gpio = gpio
        self._pin = solenoid_pin_name
        # Safety: ensure solenoid is off at construction (flap closed)
        self._gpio.write_output(self._pin, False)

    def open(self):
        """Energize solenoid valve (cylinder extends, flap opens)."""
        self._gpio.write_output(self._pin, True)

    def close(self):
        """De-energize solenoid valve (spring return closes flap)."""
        self._gpio.write_output(self._pin, False)

    def disable(self):
        """De-energize solenoid valve (same as close — spring return is fail-safe)."""
        self._gpio.write_output(self._pin, False)
