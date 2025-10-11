"""Full integration test: Live lap simulation with real DRS and Telemetry apps.

This test runs the actual production DRS and Telemetry apps against simulated
hardware (VirtualCar). The telemetry dashboard is served at http://localhost:5000
and you can watch the simulation in real-time.

Run with:
    pytest tests/simulation/test_lap_simulation_live.py -v -s

Or:
    make test-sim
"""

import sys
from pathlib import Path
import time
import yaml
from threading import Thread, Event
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.simulation.mock_hardware import VirtualCar
from tests.simulation.virtual_driver import VirtualDriver
from tests.simulation.simulated_hardware import (
    SimulatedGPIOController,
    SimulatedServoController,
    SimulatedOBDInterface,
)

# Import real apps
from apps.drs.main import DRSApp
from apps.telemetry.main import TelemetryApp
from libs.util import load_config


class LiveSimulation:
    """Full integration test with real apps and simulated hardware."""

    def __init__(self, scenario_path: str):
        """
        Initialize live simulation.

        Args:
            scenario_path: Path to track scenario YAML file
        """
        with open(scenario_path) as f:
            self.scenario = yaml.safe_load(f)

        # Create virtual car and driver
        self.car = VirtualCar(initial_speed_kph=100)
        self.driver = VirtualDriver(self.scenario)

        # Data logging
        self.telemetry_log = []
        self.drs_events = []
        self.current_lap_telemetry = []  # Track current lap's telemetry separately

        # App threads
        self.drs_thread = None
        self.telemetry_thread = None
        self.drs_app = None
        self.telemetry_app = None

        # Stop event for clean shutdown
        self._stop_event = Event()

    def _create_simulated_config(self, base_config: dict) -> dict:
        """
        Create configuration for simulated hardware.

        Args:
            base_config: Base configuration from YAML

        Returns:
            Modified config with simulated hardware
        """
        config = base_config.copy()

        # Disable file logging for tests
        if "logging" in config:
            config["logging"]["file"] = None

        return config

    def _init_drs_app(self):
        """Initialize DRS app with simulated hardware."""
        # Load configuration
        drs_config_path = Path(__file__).parent.parent.parent / "config" / "roles" / "drs.yaml"
        car_config_path = Path(__file__).parent.parent.parent / "config" / "cars" / "car1.yaml"

        config = load_config(str(drs_config_path), str(car_config_path))
        config = self._create_simulated_config(config)

        # Create DRS app with simulated hardware
        # We'll monkey-patch the hardware initialization
        self.drs_app = DRSApp(config, dry_run=True)

        # Replace hardware with simulated versions
        self.drs_app.gpio = SimulatedGPIOController(self.car, config.get("gpio", {}))
        self.drs_app.servo = SimulatedServoController(
            self.car,
            channel=config.get("servo", {}).get("channel", 0),
            min_angle=config.get("servo", {}).get("closed_angle", 0),
            max_angle=config.get("servo", {}).get("open_angle", 90),
        )

        # Re-register callbacks with simulated GPIO
        self.drs_app.gpio.register_callback("DRS_BTN", self.drs_app._on_button_press)
        self.drs_app.gpio.register_callback("BRAKE_SWITCH", self.drs_app._on_brake_change)

        # Set servo to closed position
        servo_config = config.get("servo", {})
        self.drs_app.servo.set_angle(servo_config.get("closed_angle", 0))

    def _init_telemetry_app(self):
        """Initialize Telemetry app with simulated hardware."""
        # Load configuration
        telemetry_config_path = (
            Path(__file__).parent.parent.parent / "config" / "roles" / "telemetry.yaml"
        )
        car_config_path = Path(__file__).parent.parent.parent / "config" / "cars" / "car1.yaml"

        config = load_config(str(telemetry_config_path), str(car_config_path))
        config = self._create_simulated_config(config)

        # Create Telemetry app
        self.telemetry_app = TelemetryApp(config, dry_run=True)

        # Replace OBD interface with simulated version
        self.telemetry_app.obd_interface = SimulatedOBDInterface(self.car)
        self.telemetry_app.obd_collector.obd = self.telemetry_app.obd_interface

    def start_apps(self):
        """Start DRS and Telemetry apps in background threads."""
        print(f"\n{'='*70}")
        print(f"🏁 Starting Live Lap Simulation: {self.scenario['track']['name']}")
        print(f"{'='*70}")
        print(f"")
        print(f"✅ DRS API running at: http://localhost:5001/status")
        print(f"✅ Telemetry Dashboard at: http://localhost:5000")
        print(f"")
        print(f"📊 Open your browser to see live telemetry data!")
        print(f"")

        # Initialize apps
        self._init_drs_app()
        self._init_telemetry_app()

        # Start DRS app in background
        self.drs_thread = Thread(target=self.drs_app.run, daemon=True)
        self.drs_thread.start()

        # Start Telemetry app in background
        self.telemetry_thread = Thread(target=self.telemetry_app.run, daemon=True)
        self.telemetry_thread.start()

        # Give servers time to start and wait for dashboard to be ready
        print("⏳ Waiting for dashboard to initialize...")
        time.sleep(2.0)

        # Wait for dashboard to be created (up to 5 seconds)
        for i in range(50):
            if hasattr(self.telemetry_app, 'dashboard') and self.telemetry_app.dashboard:
                print("✅ Dashboard ready!")
                break
            time.sleep(0.1)
        else:
            print("⚠️  Warning: Dashboard not initialized after 5 seconds")

    def run_laps(self, num_laps: int = 1, timestep_s: float = 0.05, realtime: bool = True) -> tuple:
        """
        Simulate driving for N laps with real apps running.

        Args:
            num_laps: Number of laps to simulate
            timestep_s: Simulation time step (seconds)
            realtime: If True, run simulation in real-time (sleep between steps)

        Returns:
            Tuple of (telemetry_log, drs_events)
        """
        track_length = self.scenario["track"]["length_m"]
        simulation_time = 0.0

        for lap in range(num_laps):
            lap_start_position = self.car.position_m
            lap_start_time = simulation_time
            self.current_lap_telemetry = []  # Reset for new lap

            print(f"\n--- Lap {lap + 1}/{num_laps} ---")

            while self.car.position_m < lap_start_position + track_length:
                # Check if simulation should stop
                if self._stop_event.is_set():
                    break

                step_start = time.time()

                # Get virtual driver inputs
                lap_position = (self.car.position_m - lap_start_position) % track_length
                inputs = self.driver.update(lap_position, self.car.speed_kph, timestep_s)

                # Apply inputs to car (these will be read by simulated GPIO/OBD)
                self.car.brake_pressed = inputs["brake"]
                self.car.drs_button_pressed = inputs["drs_button"]

                # Update car physics
                self.car.update(timestep_s, target_speed=inputs["target_speed"])

                # Apps are running in background, polling the simulated hardware
                # No need to explicitly call update() on them

                # Log telemetry (from the actual telemetry app)
                sector_name = self.driver.get_current_sector_name(lap_position)
                obd_data = self.car.get_obd_data()
                drs_status = self.drs_app.get_status()

                telemetry_entry = {
                    "time": simulation_time,
                    "lap": lap + 1,
                    "position_m": lap_position,
                    "sector": sector_name,
                    "speed_kph": obd_data["SPEED"],
                    "rpm": obd_data["RPM"],
                    "coolant_temp": obd_data["COOLANT_TEMP"],
                    "throttle": obd_data["THROTTLE_POS"],
                    "drs_active": drs_status["active"],
                    "brake": self.car.brake_pressed,
                }
                self.telemetry_log.append(telemetry_entry)
                self.current_lap_telemetry.append(telemetry_entry)

                # Push telemetry sample to dashboard (continuous logging)
                if hasattr(self, 'telemetry_app') and self.telemetry_app:
                    if hasattr(self.telemetry_app, 'dashboard') and self.telemetry_app.dashboard:
                        # Convert to format expected by add_telemetry_sample
                        sample = {
                            'timestamp': simulation_time,
                            'speed_kph': obd_data["SPEED"],
                            'rpm': obd_data["RPM"],
                            'coolant_temp': obd_data["COOLANT_TEMP"],
                            'throttle': obd_data["THROTTLE_POS"],
                            'drs_active': drs_status["active"],
                            'brake': self.car.brake_pressed,
                            'sector': sector_name,
                        }
                        self.telemetry_app.dashboard.session_data.add_telemetry_sample(sample)

                # Track DRS state changes
                if len(self.telemetry_log) > 1:
                    prev_drs = self.telemetry_log[-2]["drs_active"]
                    curr_drs = telemetry_entry["drs_active"]

                    if curr_drs != prev_drs:
                        event = "DRS_OPEN" if curr_drs else "DRS_CLOSE"
                        event_data = {
                            "time": simulation_time,
                            "lap": lap + 1,
                            "event": event,
                            "speed_kph": obd_data["SPEED"],
                            "sector": sector_name,
                        }
                        self.drs_events.append(event_data)

                        # DRS events are now tracked automatically from telemetry state changes
                        # No need to manually pass events to dashboard

                        # Print DRS events to console
                        if event == "DRS_OPEN":
                            print(
                                f"  [DRS] ACTIVATED @ {obd_data['SPEED']:.1f} km/h "
                                f"(Sector: {sector_name})"
                            )
                        else:
                            print(
                                f"  [DRS] DEACTIVATED @ {obd_data['SPEED']:.1f} km/h "
                                f"({'brake' if self.car.brake_pressed else 'button'})"
                            )

                # Advance simulation time
                simulation_time += timestep_s

                # Real-time mode: sleep to match simulation timestep
                if realtime:
                    step_elapsed = time.time() - step_start
                    sleep_time = max(0, timestep_s - step_elapsed)
                    time.sleep(sleep_time)

            if self._stop_event.is_set():
                break

            # Lap complete
            lap_time = simulation_time - lap_start_time
            print(f"  Lap {lap + 1} complete: {lap_time:.2f}s")

            # Mark lap completion in dashboard
            if hasattr(self, 'telemetry_app') and self.telemetry_app:
                if hasattr(self.telemetry_app, 'dashboard') and self.telemetry_app.dashboard:
                    # Mark the lap at the current simulation time
                    marker = self.telemetry_app.dashboard.session_data.mark_lap(
                        timestamp=simulation_time,
                        note=f"Lap time: {lap_time:.2f}s"
                    )
                    if 'error' not in marker:
                        print(f"  📊 Lap {lap + 1} marked (time: {lap_time:.2f}s)")
                    else:
                        print(f"  ⚠️  Failed to mark lap: {marker['error']}")
                else:
                    print(f"  ⚠️  Dashboard not available to mark lap")

        print(f"\n{'='*70}")
        print(f"✅ Simulation complete!")
        print(f"   Total DRS events: {len(self.drs_events)}")
        print(f"   Telemetry samples: {len(self.telemetry_log)}")
        print(f"{'='*70}\n")

        # Mark session complete - stop dashboard from collecting more data
        if hasattr(self, 'telemetry_app') and self.telemetry_app:
            self.telemetry_app.dashboard.session_data.mark_complete()
            print("📊 Dashboard session marked complete - plots are final\n")

        return self.telemetry_log, self.drs_events

    def shutdown(self):
        """Shutdown apps and cleanup."""
        print("Shutting down simulation...")
        self._stop_event.set()

        if self.drs_app:
            self.drs_app.shutdown()
        if self.telemetry_app:
            self.telemetry_app.shutdown()

        # Give threads time to stop
        time.sleep(1.0)


@pytest.mark.simulation
@pytest.mark.slow
def test_laguna_seca_lap_live():
    """Full integration test with real DRS and Telemetry apps."""
    scenario_path = Path(__file__).parent / "scenarios" / "laguna_seca.yaml"

    sim = LiveSimulation(str(scenario_path))

    try:
        # Start the apps (DRS API and Telemetry Dashboard)
        sim.start_apps()

        # Run simulation
        telemetry, drs_events = sim.run_laps(num_laps=2)

        # === ASSERTIONS ===

        print("\n✅ Simulation complete - Running assertions...")

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
        print(f"   DRS activated in sectors: {activation_sectors}")

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
        print(f"   Laps: 2")
        print(f"   Telemetry samples: {len(telemetry)}")
        print(f"   DRS events: {len(drs_events)}")
        print(f"   Speed range: {min(speeds):.1f} - {max(speeds):.1f} km/h")
        print(f"   DRS activations: {len(drs_activations)}")
        print(f"\n✅ All assertions passed!\n")

        # Keep dashboard alive for interactive viewing
        print(f"{'='*70}")
        print(f"📊 Dashboard is still running!")
        print(f"   Dashboard: http://localhost:5000")
        print(f"   DRS API: http://localhost:5001/status")
        print(f"")
        print(f"   Press Ctrl+C to exit...")
        print(f"{'='*70}\n")

        try:
            # Keep running until user interrupts
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n\nShutting down...")

    finally:
        # Always shutdown cleanly
        sim.shutdown()


if __name__ == "__main__":
    # Allow running simulation directly for development
    print("Running live lap simulation directly (not via pytest)...")
    scenario_path = Path(__file__).parent / "scenarios" / "laguna_seca.yaml"

    sim = LiveSimulation(str(scenario_path))

    try:
        sim.start_apps()
        sim.run_laps(num_laps=3)  # Run more laps when running manually
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
    finally:
        sim.shutdown()
