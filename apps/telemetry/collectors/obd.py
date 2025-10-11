"""OBD-II data collector."""

import time
from threading import Thread, Event
from typing import Dict, List, Optional

from libs.hw import OBDInterface


class OBDCollector:
    """Collects OBD-II data in background thread."""

    def __init__(
        self,
        obd_interface: OBDInterface,
        pids: List[str],
        update_rate_hz: float = 10.0,
        logger=None,
    ):
        """
        Initialize OBD collector.

        Args:
            obd_interface: OBD interface instance
            pids: List of OBD command names to query
            update_rate_hz: Data collection rate (Hz)
            logger: Logger instance
        """
        self.obd = obd_interface
        self.pids = pids
        self.update_interval = 1.0 / update_rate_hz
        self.logger = logger

        self.latest_data: Dict[str, Optional[float]] = {}
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
            self.logger.info(f"OBD collector started (rate: {1.0/self.update_interval:.1f} Hz)")

    def stop(self):
        """Stop collecting data."""
        self.running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=2.0)

        if self.logger:
            self.logger.info("OBD collector stopped")

    def _collect_loop(self):
        """Background data collection loop."""
        while not self._stop_event.is_set():
            start_time = time.time()

            # Query all PIDs
            data = self.obd.query_multiple(self.pids)
            self.latest_data = data

            # Log any failed queries
            if self.logger:
                failed = [pid for pid, value in data.items() if value is None]
                if failed:
                    self.logger.debug(f"Failed to read OBD PIDs: {failed}")

            # Maintain update rate
            elapsed = time.time() - start_time
            sleep_time = max(0, self.update_interval - elapsed)
            self._stop_event.wait(sleep_time)

    def get_latest_data(self) -> Dict[str, Optional[float]]:
        """Get most recent OBD data."""
        return self.latest_data.copy()

    def get_data_with_timestamp(self) -> Dict:
        """Get OBD data with timestamp."""
        return {"timestamp": time.time(), "data": self.latest_data.copy()}
