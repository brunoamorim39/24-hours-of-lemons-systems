"""Custom metrics collector for DRS and other non-OBD data."""

import time
from threading import Thread, Event
from typing import Dict, Optional

import requests


class CustomMetricsCollector:
    """Collects custom metrics from local APIs (DRS, radio, etc.)."""

    def __init__(self, endpoints: Dict[str, str], update_rate_hz: float = 2.0, logger=None):
        """
        Initialize custom metrics collector.

        Args:
            endpoints: Dict mapping metric names to API URLs
                      e.g., {"drs": "http://localhost:5001/status"}
            update_rate_hz: Data collection rate (Hz)
            logger: Logger instance
        """
        self.endpoints = endpoints
        self.update_interval = 1.0 / update_rate_hz
        self.logger = logger

        self.latest_data: Dict[str, Optional[dict]] = {}
        self.running = False
        self._thread: Optional[Thread] = None
        self._stop_event = Event()

    def start(self):
        """Start collecting data in background thread."""
        if self.running:
            return

        self.running = True
        self._stop_event.clear()

        self._thread = Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

        if self.logger:
            self.logger.info(
                f"Custom metrics collector started (rate: {1.0/self.update_interval:.1f} Hz)"
            )

    def stop(self):
        """Stop collecting data."""
        self.running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=2.0)

        if self.logger:
            self.logger.info("Custom metrics collector stopped")

    def _collect_loop(self):
        """Background data collection loop."""
        while not self._stop_event.is_set():
            start_time = time.time()

            # Query all endpoints
            for name, url in self.endpoints.items():
                try:
                    response = requests.get(url, timeout=1.0)
                    if response.status_code == 200:
                        self.latest_data[name] = response.json()
                    else:
                        self.latest_data[name] = None
                        if self.logger:
                            self.logger.debug(
                                f"Failed to read {name}: HTTP {response.status_code}"
                            )
                except Exception as e:
                    self.latest_data[name] = None
                    if self.logger:
                        self.logger.debug(f"Failed to read {name}: {e}")

            # Maintain update rate
            elapsed = time.time() - start_time
            sleep_time = max(0, self.update_interval - elapsed)
            self._stop_event.wait(sleep_time)

    def get_latest_data(self) -> Dict[str, Optional[dict]]:
        """Get most recent custom metrics."""
        return self.latest_data.copy()

    def get_data_with_timestamp(self) -> Dict:
        """Get custom metrics with timestamp."""
        return {"timestamp": time.time(), "data": self.latest_data.copy()}
