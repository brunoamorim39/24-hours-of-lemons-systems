"""Servo controller using PCA9685 PWM driver with safety limits."""

import time
from typing import Optional


class ServoController:
    """Abstraction for controlling servos via PCA9685 PWM driver."""

    def __init__(
        self,
        channel: int,
        min_angle: float = 0.0,
        max_angle: float = 180.0,
        min_pulse: int = 150,
        max_pulse: int = 600,
        i2c_address: int = 0x40,
        dry_run: bool = False,
    ):
        """
        Initialize servo controller.

        Args:
            channel: PCA9685 channel (0-15)
            min_angle: Minimum safe angle (degrees)
            max_angle: Maximum safe angle (degrees)
            min_pulse: PWM pulse width for min_angle (μs)
            max_pulse: PWM pulse width for max_angle (μs)
            i2c_address: I2C address of PCA9685
            dry_run: If True, mock servo without actual hardware
        """
        self.channel = channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.dry_run = dry_run
        self.current_angle: Optional[float] = None

        if not dry_run:
            try:
                from adafruit_pca9685 import PCA9685
                from board import SCL, SDA
                import busio

                i2c_bus = busio.I2C(SCL, SDA)
                self.pca = PCA9685(i2c_bus, address=i2c_address)
                self.pca.frequency = 50  # Standard servo frequency (50 Hz)
            except ImportError:
                print("Warning: PCA9685 library not available, forcing dry-run mode")
                self.dry_run = True

    def set_angle(self, angle: float, transition_time: float = 0.0):
        """
        Set servo to specified angle with optional smooth transition.

        Args:
            angle: Target angle in degrees
            transition_time: Time to reach target (seconds), 0 for instant

        Raises:
            ValueError: If angle is outside safe range
        """
        # Safety check: enforce angle limits
        if angle < self.min_angle or angle > self.max_angle:
            raise ValueError(
                f"Angle {angle}° outside safe range [{self.min_angle}°, {self.max_angle}°]"
            )

        if transition_time > 0 and self.current_angle is not None:
            # Smooth transition
            steps = int(transition_time / 0.02)  # 20ms per step (50Hz)
            angle_step = (angle - self.current_angle) / steps

            for i in range(steps):
                intermediate_angle = self.current_angle + (angle_step * i)
                self._write_angle(intermediate_angle)
                time.sleep(0.02)

        # Final position
        self._write_angle(angle)
        self.current_angle = angle

    def _write_angle(self, angle: float):
        """Internal method to write angle to hardware."""
        # Convert angle to PWM pulse width
        pulse_width = self._angle_to_pulse(angle)

        if self.dry_run:
            print(f"[SERVO DRY-RUN] Channel {self.channel}: {angle:.1f}° ({pulse_width}μs)")
        else:
            # PCA9685 uses 12-bit values (0-4095) at 50Hz
            # duty_cycle = pulse_width_us * 4096 / 20000
            duty_cycle = int(pulse_width * 4096 / 20000)
            self.pca.channels[self.channel].duty_cycle = duty_cycle

    def _angle_to_pulse(self, angle: float) -> int:
        """Convert angle to PWM pulse width (microseconds)."""
        # Linear interpolation between min and max pulse widths
        pulse_range = self.max_pulse - self.min_pulse
        angle_range = self.max_angle - self.min_angle
        pulse_width = self.min_pulse + (angle - self.min_angle) * (pulse_range / angle_range)
        return int(pulse_width)

    def get_angle(self) -> Optional[float]:
        """Get current servo angle."""
        return self.current_angle

    def disable(self):
        """Disable servo (stop sending PWM signal)."""
        if self.dry_run:
            print(f"[SERVO DRY-RUN] Channel {self.channel}: DISABLED")
        else:
            self.pca.channels[self.channel].duty_cycle = 0

    def cleanup(self):
        """Clean up servo resources."""
        self.disable()
        if not self.dry_run:
            self.pca.deinit()
