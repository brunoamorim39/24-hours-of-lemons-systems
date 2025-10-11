"""Virtual driver that follows track scenarios with realistic behavior."""

import time
from typing import Dict, List, Optional


class VirtualDriver:
    """Simulates driver inputs based on track position and conditions."""

    def __init__(self, scenario: dict, reaction_time_ms: int = 200):
        """
        Initialize virtual driver.

        Args:
            scenario: Track scenario dict loaded from YAML
            reaction_time_ms: Human reaction time for inputs
        """
        self.scenario = scenario
        self.reaction_time = reaction_time_ms / 1000.0
        self.track_length = scenario["track"]["length_m"]
        self.sectors = scenario["track"]["sectors"]

        # Driver behavior config
        self.driver_config = scenario.get("driver_behavior", {})
        self.drs_threshold_kph = self.driver_config.get("drs_activation_threshold_kph", 140)

        # State tracking
        self.current_sector_idx = 0
        self.drs_requested = False
        self.scheduled_inputs: List[dict] = []

    def update(
        self, position_m: float, speed_kph: float, dt: float
    ) -> Dict[str, bool | float]:
        """
        Update driver inputs based on track position and speed.

        Args:
            position_m: Current position on track (meters)
            speed_kph: Current speed (km/h)
            dt: Time delta (seconds)

        Returns:
            Dict of driver inputs: {"brake": bool, "drs_button": bool, "target_speed": float}
        """
        # Wrap position to track length
        position_m = position_m % self.track_length

        # Find current sector
        sector = self._get_sector(position_m)
        if sector is None:
            return {"brake": False, "drs_button": False, "target_speed": speed_kph}

        # Determine target speed for this sector
        if "speed_kph" in sector:
            # Speed is [entry, exit] - interpolate based on position in sector
            start_m = sector["start_m"]
            end_m = sector["end_m"]
            sector_progress = (position_m - start_m) / (end_m - start_m)
            entry_speed, exit_speed = sector["speed_kph"]
            target_speed = entry_speed + (exit_speed - entry_speed) * sector_progress
        else:
            target_speed = speed_kph

        # Braking logic
        brake = sector.get("brake", False)

        # DRS button logic
        drs_button = False
        in_drs_zone = sector.get("drs_zone", False)

        if in_drs_zone and speed_kph >= self.drs_threshold_kph:
            if not self.drs_requested:
                # Press button on first entry to DRS zone
                drs_button = True
                self.drs_requested = True
            # Keep button pressed while in zone (hold for multiple timesteps)
            elif self.drs_requested:
                drs_button = True
        else:
            # Release button when leaving DRS zone
            self.drs_requested = False
            drs_button = False

        return {
            "brake": brake,
            "drs_button": drs_button,
            "target_speed": target_speed,
        }

    def _get_sector(self, position_m: float) -> Optional[dict]:
        """Find the sector for a given track position."""
        for sector in self.sectors:
            if sector["start_m"] <= position_m < sector["end_m"]:
                return sector
        return None

    def get_current_sector_name(self, position_m: float) -> str:
        """Get name of current sector."""
        sector = self._get_sector(position_m % self.track_length)
        return sector["name"] if sector else "Unknown"
