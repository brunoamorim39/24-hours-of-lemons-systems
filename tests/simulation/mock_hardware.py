"""Mock hardware simulator for realistic car physics and sensor responses."""

import time
from typing import Dict, Optional


class VirtualCar:
    """Simulates car physics and provides mock sensor data."""

    def __init__(self, initial_speed_kph: float = 100):
        """
        Initialize virtual car.

        Args:
            initial_speed_kph: Starting speed
        """
        # Physical state
        self.speed_kph = initial_speed_kph
        self.position_m = 0.0
        self.acceleration = 0.0

        # Engine state
        self.rpm = 2000
        self.throttle_pos = 50.0
        self.engine_load = 50.0
        self.coolant_temp = 85.0

        # Control inputs
        self.brake_pressed = False
        self.drs_button_pressed = False

        # DRS state (controlled by DRS app)
        self.drs_open = False

        # Track simulation context
        self.current_sector = None
        self.target_speed = initial_speed_kph

    def update(self, dt: float, target_speed: Optional[float] = None):
        """
        Update car physics for one timestep.

        Args:
            dt: Time step (seconds)
            target_speed: Target speed for this sector (km/h)
        """
        if target_speed is not None:
            self.target_speed = target_speed

        # DRS effect: 5% speed boost when open on straights
        drs_multiplier = 1.05 if self.drs_open else 1.0

        # Determine if we need to slow down
        effective_target = self.target_speed * drs_multiplier
        speed_error = effective_target - self.speed_kph

        # Braking physics
        if self.brake_pressed and self.speed_kph > effective_target:
            # Hard braking: -120 km/h per second (only if above target)
            self.acceleration = -120.0
            self.throttle_pos = 0.0
        else:
            # Proportional controller to reach target speed
            self.acceleration = speed_error * 0.8  # P gain

            # Throttle position based on acceleration demand
            self.throttle_pos = min(100.0, max(0.0, 50.0 + speed_error * 0.5))

        # Update speed
        self.speed_kph += self.acceleration * dt
        # Minimum speed to prevent infinite loops (1 km/h = ~0.28 m/s)
        self.speed_kph = max(1.0, self.speed_kph)  # Can't stop completely in simulation

        # Update position
        speed_ms = self.speed_kph / 3.6
        self.position_m += speed_ms * dt

        # Engine RPM model (simple gear ratio simulation)
        # Assume 6-speed transmission, RPM roughly proportional to speed
        if self.speed_kph < 1:
            self.rpm = 1000  # Idle
        else:
            # Rough mapping: 2000 RPM @ 60 km/h, 6000 RPM @ 180 km/h
            self.rpm = int(1000 + (self.speed_kph / 180.0) * 5000)
            self.rpm = min(7000, max(1000, self.rpm))

        # Engine load based on throttle and speed
        self.engine_load = self.throttle_pos * 0.8

        # Coolant temp: slowly increases with engine load, cools when coasting
        temp_delta = (self.engine_load / 100.0 * 0.5 - 0.2) * dt
        self.coolant_temp += temp_delta
        self.coolant_temp = max(75.0, min(105.0, self.coolant_temp))

    def get_obd_data(self) -> Dict[str, float]:
        """Get mock OBD-II sensor data."""
        return {
            "SPEED": round(self.speed_kph, 1),
            "RPM": self.rpm,
            "COOLANT_TEMP": round(self.coolant_temp, 1),
            "THROTTLE_POS": round(self.throttle_pos, 1),
            "ENGINE_LOAD": round(self.engine_load, 1),
        }

    def get_gpio_state(self, pin_name: str) -> bool:
        """Get mock GPIO pin state."""
        if pin_name == "BRAKE_SWITCH":
            return self.brake_pressed
        elif pin_name == "DRS_BTN":
            return self.drs_button_pressed
        else:
            return False

    def set_gpio_output(self, pin_name: str, value: bool):
        """Simulate GPIO output (e.g., DRS LED)."""
        # In simulation, we don't need to track LED state
        pass

    def set_servo_angle(self, angle: float):
        """Simulate servo movement (DRS wing position)."""
        # Assume open_angle = 90, closed_angle = 0
        self.drs_open = angle > 45  # Simple threshold

    def reset_position(self):
        """Reset position to start of track."""
        self.position_m = 0.0
