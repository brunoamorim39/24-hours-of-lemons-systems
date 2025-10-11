"""Integration test: Full lap simulation with DRS and telemetry."""

import sys
from pathlib import Path
import time
import yaml

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.simulation.mock_hardware import VirtualCar
from tests.simulation.virtual_driver import VirtualDriver


class MockDRSApp:
    """Mock DRS app for simulation testing."""

    def __init__(self, car: VirtualCar):
        self.car = car
        self.state = "idle"
        self.button_was_pressed = False

    def update(self):
        """Update DRS state based on button input."""
        # Check button press (edge detection)
        button_now = self.car.get_gpio_state("DRS_BTN")

        if button_now and not self.button_was_pressed:
            # Button just pressed - toggle DRS
            if self.state == "idle":
                self._activate_drs()
            elif self.state == "active":
                self._deactivate_drs()

        self.button_was_pressed = button_now

        # Safety: brake disables DRS
        if self.car.get_gpio_state("BRAKE_SWITCH") and self.state == "active":
            self._deactivate_drs()

    def _activate_drs(self):
        """Activate DRS."""
        self.state = "active"
        self.car.set_servo_angle(90)  # Open
        print(f"  [DRS] ACTIVATED @ {self.car.speed_kph:.1f} km/h")

    def _deactivate_drs(self):
        """Deactivate DRS."""
        self.state = "idle"
        self.car.set_servo_angle(0)  # Closed
        print(f"  [DRS] DEACTIVATED @ {self.car.speed_kph:.1f} km/h")

    def is_active(self) -> bool:
        """Check if DRS is active."""
        return self.state == "active"

    def get_status(self) -> dict:
        """Get DRS status."""
        return {"state": self.state, "active": self.is_active()}


class LapSimulation:
    """Full integration test: drive laps with DRS and telemetry."""

    def __init__(self, scenario_path: str):
        """
        Initialize lap simulation.

        Args:
            scenario_path: Path to track scenario YAML file
        """
        with open(scenario_path) as f:
            self.scenario = yaml.safe_load(f)

        self.car = VirtualCar(initial_speed_kph=100)
        self.driver = VirtualDriver(self.scenario)
        self.drs_app = MockDRSApp(self.car)

        self.telemetry_log = []
        self.drs_events = []

    def run_laps(self, num_laps: int = 1, timestep_s: float = 0.05) -> tuple:
        """
        Simulate driving for N laps.

        Args:
            num_laps: Number of laps to simulate
            timestep_s: Simulation time step (seconds)

        Returns:
            Tuple of (telemetry_log, drs_events)
        """
        track_length = self.scenario["track"]["length_m"]
        simulation_time = 0.0

        print(f"\n{'='*60}")
        print(f"Starting {num_laps}-lap simulation: {self.scenario['track']['name']}")
        print(f"{'='*60}")

        for lap in range(num_laps):
            lap_start_position = self.car.position_m
            lap_start_time = simulation_time

            print(f"\n--- Lap {lap + 1}/{num_laps} ---")

            while self.car.position_m < lap_start_position + track_length:
                # Get virtual driver inputs
                lap_position = (self.car.position_m - lap_start_position) % track_length
                inputs = self.driver.update(lap_position, self.car.speed_kph, timestep_s)

                # Apply inputs to car
                self.car.brake_pressed = inputs["brake"]
                self.car.drs_button_pressed = inputs["drs_button"]

                # Update car physics
                self.car.update(timestep_s, target_speed=inputs["target_speed"])

                # Update DRS app
                self.drs_app.update()

                # Log telemetry
                sector_name = self.driver.get_current_sector_name(lap_position)
                obd_data = self.car.get_obd_data()

                telemetry_entry = {
                    "time": simulation_time,
                    "lap": lap + 1,
                    "position_m": lap_position,
                    "sector": sector_name,
                    "speed_kph": obd_data["SPEED"],
                    "rpm": obd_data["RPM"],
                    "coolant_temp": obd_data["COOLANT_TEMP"],
                    "throttle": obd_data["THROTTLE_POS"],
                    "drs_active": self.drs_app.is_active(),
                    "brake": self.car.brake_pressed,
                }
                self.telemetry_log.append(telemetry_entry)

                # Track DRS state changes
                if len(self.telemetry_log) > 1:
                    prev_drs = self.telemetry_log[-2]["drs_active"]
                    curr_drs = telemetry_entry["drs_active"]

                    if curr_drs != prev_drs:
                        event = "DRS_OPEN" if curr_drs else "DRS_CLOSE"
                        self.drs_events.append(
                            {
                                "time": simulation_time,
                                "lap": lap + 1,
                                "event": event,
                                "speed_kph": obd_data["SPEED"],
                                "sector": sector_name,
                            }
                        )

                # Advance simulation time
                simulation_time += timestep_s

            # Lap complete
            lap_time = simulation_time - lap_start_time
            print(f"  Lap {lap + 1} complete: {lap_time:.2f}s")

        print(f"\n{'='*60}")
        print(f"Simulation complete!")
        print(f"Total DRS events: {len(self.drs_events)}")
        print(f"Telemetry samples: {len(self.telemetry_log)}")
        print(f"{'='*60}\n")

        return self.telemetry_log, self.drs_events


@pytest.mark.simulation
def test_laguna_seca_lap():
    """Validate DRS and telemetry over a full lap at Laguna Seca."""
    scenario_path = Path(__file__).parent / "scenarios" / "laguna_seca.yaml"

    sim = LapSimulation(str(scenario_path))
    telemetry, drs_events = sim.run_laps(num_laps=2)

    # === ASSERTIONS ===

    # 1. Should have telemetry data
    assert len(telemetry) > 0, "No telemetry data collected"

    # 2. Should have DRS events (at least 2 activations per lap)
    assert len(drs_events) >= 4, f"Expected at least 4 DRS events, got {len(drs_events)}"

    # 3. DRS should only activate in designated zones
    for event in drs_events:
        if event["event"] == "DRS_OPEN":
            # Check speed threshold
            assert (
                event["speed_kph"] >= 140
            ), f"DRS opened at {event['speed_kph']} km/h (below 140 threshold)"

    # 4. DRS should activate in DRS zones
    drs_activations = [e for e in drs_events if e["event"] == "DRS_OPEN"]
    activation_sectors = set(e["sector"] for e in drs_activations)
    print(f"\nDRS activated in sectors: {activation_sectors}")

    # Should activate in at least one of the DRS zones
    assert len(activation_sectors) > 0, "DRS never activated"

    # 5. Verify telemetry captured key moments
    speeds = [t["speed_kph"] for t in telemetry]
    assert min(speeds) < 100, f"Min speed {min(speeds)} too high (expected slow corners)"
    assert max(speeds) > 160, f"Max speed {max(speeds)} too low (expected high speeds)"

    # 6. Verify brake disables DRS (safety check)
    for i, entry in enumerate(telemetry):
        if entry["brake"] and i > 0:
            # If braking, DRS should be off
            # (might take 1-2 samples to react, so check next few samples)
            for j in range(i, min(i + 3, len(telemetry))):
                if not telemetry[j]["drs_active"]:
                    break
            else:
                # DRS stayed on during braking
                pytest.fail(f"DRS remained active during braking at t={entry['time']:.2f}s")

    # 7. Print summary
    print("\n=== Test Summary ===")
    print(f"Laps: 2")
    print(f"Telemetry samples: {len(telemetry)}")
    print(f"DRS events: {len(drs_events)}")
    print(f"Speed range: {min(speeds):.1f} - {max(speeds):.1f} km/h")
    print(f"DRS activations: {len(drs_activations)}")


@pytest.mark.simulation
def test_drs_brake_safety():
    """Test that brake immediately disables DRS (safety critical)."""
    scenario_path = Path(__file__).parent / "scenarios" / "laguna_seca.yaml"

    sim = LapSimulation(str(scenario_path))

    # Manually activate DRS and then brake
    sim.car.speed_kph = 180
    sim.car.drs_button_pressed = True
    sim.drs_app.update()

    assert sim.drs_app.is_active(), "DRS should be active"

    # Apply brake
    sim.car.brake_pressed = True
    sim.drs_app.update()

    assert not sim.drs_app.is_active(), "DRS should be disabled by brake"


if __name__ == "__main__":
    # Allow running simulation directly
    print("Running lap simulation directly (not via pytest)...")
    scenario_path = Path(__file__).parent / "scenarios" / "laguna_seca.yaml"
    sim = LapSimulation(str(scenario_path))
    telemetry, drs_events = sim.run_laps(num_laps=1)

    print("\n=== DRS Events ===")
    for event in drs_events:
        print(
            f"[Lap {event['lap']}] {event['time']:6.2f}s | {event['event']:10s} | "
            f"{event['speed_kph']:5.1f} km/h | {event['sector']}"
        )
