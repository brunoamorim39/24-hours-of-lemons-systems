"""Simulated hardware adapters that bridge VirtualCar to real HAL interfaces.

These classes implement the same interface as the real hardware controllers
(GPIO, Servo, OBD) but are backed by the VirtualCar physics simulation instead
of actual hardware. This allows the real DRS and Telemetry apps to run against
the simulation.
"""

import time
from typing import Callable, Dict, List, Optional

from tests.simulation.mock_hardware import VirtualCar


class SimulatedGPIOController:
    """GPIO controller backed by VirtualCar simulation."""

    def __init__(self, car: VirtualCar, pin_config: Dict[str, int], dry_run: bool = True):
        """
        Initialize simulated GPIO controller.

        Args:
            car: VirtualCar instance to read/write state from
            pin_config: Pin configuration (ignored in simulation)
            dry_run: Must be True for simulation
        """
        self.car = car
        self.pin_config = pin_config
        self.dry_run = True  # Always dry-run
        self._callbacks: Dict[str, list] = {}
        self._last_state: Dict[str, bool] = {}

    def read_input(self, name: str, debounce_ms: int = 50) -> bool:
        """
        Read input from simulated car.

        Args:
            name: Pin name (e.g., "DRS_BTN", "BRAKE_SWITCH")
            debounce_ms: Ignored in simulation

        Returns:
            Current state of the input
        """
        current_state = self.car.get_gpio_state(name)

        # Trigger callbacks on state change
        prev_state = self._last_state.get(name, False)
        if current_state != prev_state:
            self._trigger_callbacks(name, current_state)
            self._last_state[name] = current_state

        return current_state

    def write_output(self, name: str, value: bool):
        """
        Write output to simulated car.

        Args:
            name: Pin name (e.g., "DRS_LED")
            value: Output state
        """
        self.car.set_gpio_output(name, value)

    def register_callback(self, name: str, callback: Callable[[bool], None]):
        """
        Register callback for input state changes.

        Args:
            name: Pin name
            callback: Function called with new state
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
                print(f"[SIM] Error in callback for {name}: {e}")

    def set_mock_input(self, name: str, value: bool):
        """Set mock input (compatibility method)."""
        # In simulation, inputs are controlled by VirtualDriver
        pass

    def cleanup(self):
        """Cleanup GPIO (no-op for simulation)."""
        pass


class SimulatedServoController:
    """Servo controller backed by VirtualCar simulation."""

    def __init__(
        self,
        car: VirtualCar,
        channel: int,
        min_angle: float = 0.0,
        max_angle: float = 180.0,
        min_pulse: int = 150,
        max_pulse: int = 600,
        i2c_address: int = 0x40,
        dry_run: bool = True,
    ):
        """
        Initialize simulated servo controller.

        Args:
            car: VirtualCar instance to control
            channel: Servo channel (ignored)
            min_angle: Minimum angle
            max_angle: Maximum angle
            min_pulse: Min PWM pulse (ignored)
            max_pulse: Max PWM pulse (ignored)
            i2c_address: I2C address (ignored)
            dry_run: Must be True
        """
        self.car = car
        self.channel = channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.dry_run = True
        self.current_angle: Optional[float] = None

    def set_angle(self, angle: float, transition_time: float = 0.0):
        """
        Set servo angle in simulation.

        Args:
            angle: Target angle
            transition_time: Ignored in simulation

        Raises:
            ValueError: If angle outside safe range
        """
        if angle < self.min_angle or angle > self.max_angle:
            raise ValueError(
                f"Angle {angle}° outside safe range [{self.min_angle}°, {self.max_angle}°]"
            )

        self.car.set_servo_angle(angle)
        self.current_angle = angle

    def get_angle(self) -> Optional[float]:
        """Get current servo angle."""
        return self.current_angle

    def disable(self):
        """Disable servo (no-op in simulation)."""
        pass

    def cleanup(self):
        """Cleanup servo (no-op)."""
        pass


class SimulatedOBDInterface:
    """OBD interface backed by VirtualCar simulation."""

    def __init__(self, car: VirtualCar, port: str = "/dev/ttyUSB0", baudrate: int = 38400, dry_run: bool = True):
        """
        Initialize simulated OBD interface.

        Args:
            car: VirtualCar instance to read data from
            port: Ignored
            baudrate: Ignored
            dry_run: Must be True
        """
        self.car = car
        self.port = port
        self.baudrate = baudrate
        self.dry_run = True
        self.connection = None

    def query(self, command_name: str) -> Optional[float]:
        """
        Query OBD parameter from simulated car.

        Args:
            command_name: OBD command (e.g., "SPEED", "RPM")

        Returns:
            Parameter value or None
        """
        obd_data = self.car.get_obd_data()
        return obd_data.get(command_name)

    def query_multiple(self, command_names: List[str]) -> Dict[str, Optional[float]]:
        """
        Query multiple OBD parameters.

        Args:
            command_names: List of command names

        Returns:
            Dict of command names to values
        """
        obd_data = self.car.get_obd_data()
        return {cmd: obd_data.get(cmd) for cmd in command_names}

    def is_connected(self) -> bool:
        """Check if OBD is connected (always True in simulation)."""
        return True

    def set_mock_data(self, command_name: str, value: float):
        """Set mock data (not needed - VirtualCar controls data)."""
        pass

    def get_supported_commands(self) -> List[str]:
        """Get supported commands."""
        return ["SPEED", "RPM", "COOLANT_TEMP", "THROTTLE_POS", "ENGINE_LOAD"]

    def cleanup(self):
        """Cleanup OBD (no-op)."""
        pass
