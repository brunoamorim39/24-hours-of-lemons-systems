"""OBD-II interface wrapper for reading vehicle telemetry."""

import time
from typing import Dict, List, Optional


class OBDInterface:
    """Abstraction for OBD-II communication using python-OBD library."""

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 38400, dry_run: bool = False):
        """
        Initialize OBD-II interface.

        Args:
            port: Serial port for OBD adapter (e.g., /dev/ttyUSB0)
            baudrate: Communication baud rate
            dry_run: If True, mock OBD without actual hardware
        """
        self.port = port
        self.baudrate = baudrate
        self.dry_run = dry_run
        self.connection = None
        self._mock_data: Dict[str, float] = {}

        if not dry_run:
            try:
                import obd

                self.obd = obd
                self.connection = obd.OBD(port, baudrate)

                if not self.connection.is_connected():
                    print(f"Warning: Could not connect to OBD-II on {port}, forcing dry-run")
                    self.dry_run = True
            except ImportError:
                print("Warning: python-OBD not available, forcing dry-run mode")
                self.dry_run = True

    def query(self, command_name: str) -> Optional[float]:
        """
        Query a single OBD-II parameter.

        Args:
            command_name: OBD command name (e.g., "SPEED", "RPM", "COOLANT_TEMP")

        Returns:
            Parameter value as float, or None if unavailable
        """
        if self.dry_run:
            return self._mock_data.get(command_name)

        try:
            cmd = getattr(self.obd.commands, command_name)
            response = self.connection.query(cmd)

            if response.is_null():
                return None

            # Extract numeric value
            return float(response.value.magnitude)
        except AttributeError:
            print(f"Warning: Unknown OBD command: {command_name}")
            return None
        except Exception as e:
            print(f"Error querying {command_name}: {e}")
            return None

    def query_multiple(self, command_names: List[str]) -> Dict[str, Optional[float]]:
        """
        Query multiple OBD-II parameters efficiently.

        Args:
            command_names: List of OBD command names

        Returns:
            Dict mapping command names to values
        """
        results = {}
        for cmd_name in command_names:
            results[cmd_name] = self.query(cmd_name)
        return results

    def is_connected(self) -> bool:
        """Check if OBD connection is active."""
        if self.dry_run:
            return True
        return self.connection is not None and self.connection.is_connected()

    def set_mock_data(self, command_name: str, value: float):
        """
        Set mock OBD data for testing (dry-run mode only).

        Args:
            command_name: OBD command name
            value: Mock value
        """
        if not self.dry_run:
            raise RuntimeError("set_mock_data only available in dry-run mode")
        self._mock_data[command_name] = value

    def get_supported_commands(self) -> List[str]:
        """Get list of OBD commands supported by the vehicle."""
        if self.dry_run:
            return ["SPEED", "RPM", "COOLANT_TEMP", "THROTTLE_POS", "ENGINE_LOAD"]

        if not self.is_connected():
            return []

        return [cmd.name for cmd in self.connection.supported_commands]

    def cleanup(self):
        """Clean up OBD connection."""
        if not self.dry_run and self.connection:
            self.connection.close()
