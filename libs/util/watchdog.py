"""Watchdog timer for monitoring app health."""

import time
from threading import Event, Thread
from typing import Callable, Optional


class Watchdog:
    """
    Watchdog timer to ensure app is responsive.

    If not fed within timeout period, executes a callback (e.g., restart).
    """

    def __init__(self, timeout_s: float, callback: Optional[Callable] = None):
        """
        Initialize watchdog.

        Args:
            timeout_s: Timeout in seconds before watchdog triggers
            callback: Function to call when watchdog times out
        """
        self.timeout_s = timeout_s
        self.callback = callback or self._default_callback
        self.last_fed = time.time()
        self.running = False
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    def start(self):
        """Start watchdog monitoring in background thread."""
        if self.running:
            return

        self.running = True
        self.last_fed = time.time()
        self._stop_event.clear()

        self._thread = Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def feed(self):
        """Feed the watchdog to prevent timeout."""
        self.last_fed = time.time()

    def stop(self):
        """Stop watchdog monitoring."""
        self.running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor(self):
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            time.sleep(0.1)

            if time.time() - self.last_fed > self.timeout_s:
                try:
                    self.callback()
                except Exception as e:
                    print(f"Watchdog callback error: {e}")

                # Reset timer after callback
                self.last_fed = time.time()

    @staticmethod
    def _default_callback():
        """Default callback: log and exit."""
        print("WATCHDOG TIMEOUT - App appears hung!")
        import sys

        sys.exit(1)


class HealthChecker:
    """Simple health check status tracker."""

    def __init__(self):
        self.status = "starting"
        self.last_update = time.time()
        self.errors: list = []

    def set_healthy(self):
        """Mark app as healthy."""
        self.status = "healthy"
        self.last_update = time.time()

    def set_degraded(self, reason: str):
        """Mark app as degraded (working but with issues)."""
        self.status = "degraded"
        self.errors.append({"time": time.time(), "reason": reason})
        self.last_update = time.time()

    def set_unhealthy(self, reason: str):
        """Mark app as unhealthy (not functioning)."""
        self.status = "unhealthy"
        self.errors.append({"time": time.time(), "reason": reason})
        self.last_update = time.time()

    def get_status(self) -> dict:
        """Get current health status."""
        return {
            "status": self.status,
            "uptime": time.time() - self.last_update,
            "recent_errors": self.errors[-5:],  # Last 5 errors
        }
