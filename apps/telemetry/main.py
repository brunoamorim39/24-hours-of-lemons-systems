"""Telemetry app for collecting and displaying vehicle data."""

import argparse
import sys
import time
from pathlib import Path
from threading import Thread

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from libs.hw import OBDInterface
from libs.util import load_config, setup_logging, Watchdog, HealthChecker
from apps.telemetry.collectors import OBDCollector, CustomMetricsCollector


class TelemetryApp:
    """Main telemetry application."""

    def __init__(self, config: dict, dry_run: bool = False):
        """
        Initialize telemetry app.

        Args:
            config: Merged configuration from role + car configs
            dry_run: If True, mock hardware
        """
        self.config = config
        self.dry_run = dry_run
        self.logger = setup_logging(
            "telemetry",
            level=config.get("logging", {}).get("level", "INFO"),
            log_file=config.get("logging", {}).get("file"),
        )

        self.running = False

        # Health monitoring
        self.health = HealthChecker()
        self.watchdog = Watchdog(
            timeout_s=config.get("watchdog", {}).get("timeout_s", 10.0),
            callback=self._watchdog_timeout,
        )

        # Initialize data collectors
        self._init_collectors()

        # Dashboard server (runs in separate thread)
        self.dashboard_thread = None

    def _init_collectors(self):
        """Initialize OBD and custom metrics collectors."""
        self.logger.info("Initializing data collectors", extra={"dry_run": self.dry_run})

        # OBD collector
        obd_config = self.config.get("obd", {})
        self.obd_interface = OBDInterface(
            port=obd_config.get("port", "/dev/ttyUSB0"),
            baudrate=obd_config.get("baudrate", 38400),
            dry_run=self.dry_run,
        )

        self.obd_collector = OBDCollector(
            obd_interface=self.obd_interface,
            pids=obd_config.get("pids", ["SPEED", "RPM", "COOLANT_TEMP"]),
            update_rate_hz=obd_config.get("update_rate_hz", 10.0),
            logger=self.logger,
        )

        # Custom metrics collector
        custom_config = self.config.get("custom_metrics", {})
        self.custom_collector = CustomMetricsCollector(
            endpoints=custom_config.get("endpoints", {}),
            update_rate_hz=custom_config.get("update_rate_hz", 2.0),
            logger=self.logger,
        )

        self.health.set_healthy()

    def _watchdog_timeout(self):
        """Handle watchdog timeout."""
        self.logger.critical("Watchdog timeout - main loop appears hung!")
        self.health.set_unhealthy("Watchdog timeout")

    def get_telemetry_data(self) -> dict:
        """Get current telemetry data from all collectors."""
        obd_data = self.obd_collector.get_latest_data()
        custom_data = self.custom_collector.get_latest_data()

        return {
            "timestamp": time.time(),
            "obd": obd_data,
            "custom": custom_data,
            "health": self.health.get_status(),
        }

    def run(self):
        """Main app loop."""
        self.logger.info("Starting telemetry app", extra={"dry_run": self.dry_run})
        self.running = True

        # Start watchdog
        self.watchdog.start()

        # Start data collectors
        self.obd_collector.start()
        self.custom_collector.start()

        # Start ECharts/BMW dashboard server in background
        from apps.telemetry.echarts_dashboard import TelemetryDashboard

        dashboard_config = self.config.get("dashboard", {})

        # Create BMW-themed dashboard with interactive ECharts
        self.dashboard = TelemetryDashboard(self)

        # Start in background thread
        self.dashboard_thread = Thread(
            target=self.dashboard.run,
            kwargs={
                "host": dashboard_config.get("bind", "0.0.0.0"),
                "port": dashboard_config.get("port", 5000),
                "debug": False,
            },
            daemon=True,
        )
        self.dashboard_thread.start()

        # Main loop
        try:
            while self.running:
                # Feed watchdog
                self.watchdog.feed()

                # Check collector health
                if not self.obd_interface.is_connected():
                    self.health.set_degraded("OBD connection lost")
                else:
                    self.health.set_healthy()

                # Small sleep to avoid busy-waiting
                time.sleep(0.1)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown."""
        self.logger.info("Shutting down telemetry app")
        self.running = False

        # Stop collectors
        self.obd_collector.stop()
        self.custom_collector.stop()

        # Stop watchdog
        self.watchdog.stop()

        # Cleanup hardware
        self.obd_interface.cleanup()


def main():
    """Entry point for telemetry app."""
    parser = argparse.ArgumentParser(description="Telemetry app")
    parser.add_argument(
        "--config",
        default="config/roles/telemetry.yaml",
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
    app = TelemetryApp(config, dry_run=args.dry_run)
    app.run()


if __name__ == "__main__":
    main()
