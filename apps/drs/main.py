"""DRS control app with state machine and safety interlocks."""

import argparse
import sys
import time
from enum import Enum
from pathlib import Path
from threading import Thread

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from libs.hw import GPIOController, ServoController
from libs.util import load_config, setup_logging, Watchdog, HealthChecker


class DRSState(Enum):
    """DRS system states."""

    IDLE = "idle"
    ACTIVE = "active"
    FAULT = "fault"


class DRSApp:
    """Main DRS control application with state machine."""

    def __init__(self, config: dict, dry_run: bool = False):
        """
        Initialize DRS app.

        Args:
            config: Merged configuration from role + car configs
            dry_run: If True, mock hardware
        """
        self.config = config
        self.dry_run = dry_run
        self.logger = setup_logging(
            "drs",
            level=config.get("logging", {}).get("level", "INFO"),
            log_file=config.get("logging", {}).get("file"),
        )

        # State
        self.state = DRSState.IDLE
        self.running = False

        # Health monitoring
        self.health = HealthChecker()
        self.watchdog = Watchdog(
            timeout_s=config.get("watchdog", {}).get("timeout_s", 10.0),
            callback=self._watchdog_timeout,
        )

        # Initialize hardware
        self._init_hardware()

        # API server (runs in separate thread)
        self.api_thread = None

    def _init_hardware(self):
        """Initialize GPIO and servo controllers."""
        self.logger.info("Initializing hardware", extra={"dry_run": self.dry_run})

        # GPIO
        gpio_config = self.config.get("gpio", {})
        self.gpio = GPIOController(gpio_config, dry_run=self.dry_run)

        # Servo
        servo_config = self.config.get("servo", {})
        i2c_addr = self.config.get("i2c", {}).get("PCA9685_ADDR", 0x40)
        self.servo = ServoController(
            channel=servo_config.get("channel", 0),
            min_angle=servo_config.get("closed_angle", 0),
            max_angle=servo_config.get("open_angle", 90),
            i2c_address=i2c_addr,
            dry_run=self.dry_run,
        )

        # Set servo to closed position on startup
        self.servo.set_angle(servo_config.get("closed_angle", 0))

        # Register GPIO callbacks
        self.gpio.register_callback("DRS_BTN", self._on_button_press)
        self.gpio.register_callback("BRAKE_SWITCH", self._on_brake_change)

        self.health.set_healthy()

    def _on_button_press(self, pressed: bool):
        """Handle DRS button press."""
        if not pressed:
            return  # Only act on button press, not release

        self.logger.info("DRS button pressed", extra={"current_state": self.state.value})

        if self.state == DRSState.IDLE:
            self._activate_drs()
        elif self.state == DRSState.ACTIVE:
            self._deactivate_drs()

    def _on_brake_change(self, pressed: bool):
        """Handle brake switch state change (safety interlock)."""
        if pressed and self.state == DRSState.ACTIVE:
            self.logger.warning("Brake pressed - disabling DRS")
            self._deactivate_drs()

    def _activate_drs(self):
        """Activate DRS (open wing)."""
        try:
            servo_config = self.config.get("servo", {})
            open_angle = servo_config.get("open_angle", 90)
            transition_time = servo_config.get("transition_time", 0.5)

            self.logger.info(f"Activating DRS (opening to {open_angle}°)")

            self.servo.set_angle(open_angle, transition_time=transition_time)
            self.gpio.write_output("DRS_LED", True)
            self.state = DRSState.ACTIVE

            self.logger.info("DRS activated")

        except Exception as e:
            self.logger.error(f"Failed to activate DRS: {e}")
            self.health.set_unhealthy(f"DRS activation failed: {e}")
            self.state = DRSState.FAULT

    def _deactivate_drs(self):
        """Deactivate DRS (close wing)."""
        try:
            servo_config = self.config.get("servo", {})
            closed_angle = servo_config.get("closed_angle", 0)
            transition_time = servo_config.get("transition_time", 0.5)

            self.logger.info(f"Deactivating DRS (closing to {closed_angle}°)")

            self.servo.set_angle(closed_angle, transition_time=transition_time)
            self.gpio.write_output("DRS_LED", False)
            self.state = DRSState.IDLE

            self.logger.info("DRS deactivated")

            # Clear fault state if recovering
            if self.state == DRSState.FAULT:
                self.health.set_healthy()

        except Exception as e:
            self.logger.error(f"Failed to deactivate DRS: {e}")
            self.health.set_unhealthy(f"DRS deactivation failed: {e}")
            self.state = DRSState.FAULT

    def _watchdog_timeout(self):
        """Handle watchdog timeout."""
        self.logger.critical("Watchdog timeout - main loop appears hung!")
        self.health.set_unhealthy("Watchdog timeout")
        # Force DRS closed for safety
        self._deactivate_drs()

    def get_status(self) -> dict:
        """Get current DRS status for API."""
        return {
            "state": self.state.value,
            "active": self.state == DRSState.ACTIVE,
            "servo_angle": self.servo.get_angle(),
            "health": self.health.get_status(),
        }

    def run(self):
        """Main app loop."""
        self.logger.info("Starting DRS app", extra={"dry_run": self.dry_run})
        self.running = True

        # Start watchdog
        self.watchdog.start()

        # Start API server in background
        from apps.drs.api import start_api_server

        api_config = self.config.get("api", {})
        self.api_thread = Thread(
            target=start_api_server,
            args=(self, api_config.get("port", 5001), api_config.get("bind", "0.0.0.0")),
            daemon=True,
        )
        self.api_thread.start()

        # Main loop: poll inputs
        debounce_config = self.config.get("debounce", {})
        button_debounce = debounce_config.get("button_ms", 50)
        brake_debounce = debounce_config.get("brake_ms", 20)

        try:
            while self.running:
                # Read inputs (with debouncing)
                self.gpio.read_input("DRS_BTN", debounce_ms=button_debounce)
                self.gpio.read_input("BRAKE_SWITCH", debounce_ms=brake_debounce)

                # Feed watchdog
                self.watchdog.feed()

                # Small sleep to avoid busy-waiting
                time.sleep(0.01)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown."""
        self.logger.info("Shutting down DRS app")
        self.running = False

        # Safety: ensure DRS is closed
        self._deactivate_drs()

        # Stop watchdog
        self.watchdog.stop()

        # Cleanup hardware
        self.gpio.cleanup()
        self.servo.cleanup()


def main():
    """Entry point for DRS app."""
    parser = argparse.ArgumentParser(description="DRS control app")
    parser.add_argument(
        "--config",
        default="config/roles/drs.yaml",
        help="Path to role config file",
    )
    parser.add_argument(
        "--car",
        default="config/cars/car1.yaml",
        help="Path to car-specific config file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actual hardware (for testing)",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config, args.car)

    # Create and run app
    app = DRSApp(config, dry_run=args.dry_run)
    app.run()


if __name__ == "__main__":
    main()
