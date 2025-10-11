"""Professional BMW E46 telemetry dashboard using Apache ECharts for interactive charts.

This dashboard uses ECharts (client-side JavaScript) for interactive, Grafana-style charts:
- Smooth pan/zoom interaction (drag to pan, scroll to zoom)
- Data zoom sliders for time-series analysis
- Professional racing telemetry visualization
- BMW blue/white/gray color scheme
- Live telemetry metrics + historical analysis
"""

import threading
from typing import TYPE_CHECKING, Dict, List
from datetime import datetime

import pandas as pd
from flask import Flask, render_template_string, jsonify, Response

if TYPE_CHECKING:
    from apps.telemetry.main import TelemetryApp


# BMW Color Palette
BMW_BLUE = '#1C69D4'
BMW_GRAY = '#333333'
BMW_LIGHT_GRAY = '#F5F5F5'
BMW_WHITE = '#FFFFFF'
BMW_GOLD = '#FFD700'
BMW_GREEN = '#00FF00'


class SessionData:
    """Continuous telemetry storage with manual lap marking."""

    def __init__(self):
        self.telemetry = []  # Continuous list of telemetry samples
        self.lap_markers = []  # List of {timestamp, lap_num, note}
        self.session_start = None  # First sample timestamp
        self.session_complete = False
        self.lock = threading.Lock()
        self.live_data = {}  # Most recent telemetry sample for live display

    def add_telemetry_sample(self, sample: Dict):
        """
        Add telemetry sample to continuous buffer.

        Args:
            sample: Dict with keys: timestamp, speed_kph, rpm, coolant_temp, throttle, drs_active, brake
        """
        with self.lock:
            if self.session_complete:
                return

            # Set session start on first sample
            if self.session_start is None:
                self.session_start = sample.get('timestamp', 0)

            # Add elapsed time for easier plotting
            sample['elapsed'] = sample.get('timestamp', 0) - (self.session_start or 0)

            # Determine current lap based on markers
            current_lap = len(self.lap_markers) + 1
            sample['lap'] = current_lap

            self.telemetry.append(sample)
            self.live_data = sample

    def mark_lap(self, timestamp: float = None, note: str = ""):
        """
        Mark a lap completion point.

        Args:
            timestamp: Timestamp of lap marker (defaults to most recent sample)
            note: Optional note for this lap

        Returns:
            Dict with lap_num and timestamp
        """
        with self.lock:
            if not self.telemetry:
                return {"error": "No telemetry data yet"}

            # Use most recent sample timestamp if not provided
            if timestamp is None:
                timestamp = self.telemetry[-1].get('timestamp', 0)

            lap_num = len(self.lap_markers) + 1
            marker = {
                "lap_num": lap_num,
                "timestamp": timestamp,
                "elapsed": timestamp - (self.session_start or 0),
                "note": note,
            }
            self.lap_markers.append(marker)

            print(f"[SessionData] Lap {lap_num} marked at {timestamp:.2f}s (elapsed: {marker['elapsed']:.2f}s)")
            return marker

    def get_live_data(self) -> Dict:
        """Get most recent live telemetry data."""
        with self.lock:
            return self.live_data.copy() if self.live_data else {}

    def mark_complete(self):
        """Mark session as complete - stop accepting new data."""
        with self.lock:
            self.session_complete = True

    def get_telemetry_range(self, start_time: float = None, end_time: float = None, lap_num: int = None) -> List[Dict]:
        """
        Get telemetry samples for a time range or specific lap.

        Args:
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            lap_num: Get samples for specific lap number

        Returns:
            List of telemetry samples
        """
        with self.lock:
            if lap_num is not None:
                # Get samples for specific lap
                return [s for s in self.telemetry if s.get('lap') == lap_num]

            if start_time is None and end_time is None:
                # Return all data
                return self.telemetry.copy()

            # Filter by time range
            filtered = []
            for sample in self.telemetry:
                ts = sample.get('timestamp', 0)
                if start_time is not None and ts < start_time:
                    continue
                if end_time is not None and ts > end_time:
                    continue
                filtered.append(sample)
            return filtered

    def get_summary(self) -> Dict:
        """Get session summary statistics."""
        with self.lock:
            if not self.telemetry:
                return {
                    "duration": 0,
                    "total_samples": 0,
                    "total_laps": 0,
                    "max_speed": 0,
                    "drs_activations": 0,
                }

            # Calculate DRS activations by looking at state changes
            drs_count = 0
            for i in range(1, len(self.telemetry)):
                if self.telemetry[i].get('drs_active') and not self.telemetry[i-1].get('drs_active'):
                    drs_count += 1

            speeds = [s.get('speed_kph', 0) for s in self.telemetry]
            duration = self.telemetry[-1].get('elapsed', 0) if self.telemetry else 0

            return {
                "duration": round(duration, 1),
                "total_samples": len(self.telemetry),
                "total_laps": len(self.lap_markers),
                "max_speed": round(max(speeds) if speeds else 0, 1),
                "drs_activations": drs_count,
            }


class TelemetryDashboard:
    """Flask-based dashboard with ECharts interactive visualizations."""

    def __init__(self, telemetry_app: "TelemetryApp"):
        """Initialize dashboard."""
        self.telemetry_app = telemetry_app
        self.session_data = SessionData()

        # Create Flask app
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Main dashboard page."""
            return render_template_string(DASHBOARD_HTML)

        @self.app.route("/api/summary")
        def api_summary():
            """Get session summary as JSON."""
            return jsonify(self.session_data.get_summary())

        @self.app.route("/api/live")
        def api_live():
            """Get live telemetry data as JSON."""
            live_data = self.session_data.get_live_data()

            if not live_data:
                return jsonify({
                    "speed_kph": 0,
                    "rpm": 0,
                    "coolant_temp": 0,
                    "throttle": 0,
                    "lap": 0,
                    "sector": "--",
                    "drs_active": False,
                    "brake": False,
                })

            return jsonify({
                "speed_kph": round(live_data.get("speed_kph", 0), 1),
                "rpm": int(live_data.get("rpm", 0)),
                "coolant_temp": round(live_data.get("coolant_temp", 0), 1),
                "throttle": round(live_data.get("throttle", 0), 1),
                "lap": live_data.get("lap", 0),
                "sector": live_data.get("sector", "--"),
                "drs_active": live_data.get("drs_active", False),
                "brake": live_data.get("brake", False),
            })

        @self.app.route("/api/mark_lap", methods=["POST"])
        def mark_lap():
            """Mark a lap completion point."""
            from flask import request
            data = request.get_json() or {}
            note = data.get("note", "")

            result = self.session_data.mark_lap(note=note)
            return jsonify(result)

        @self.app.route("/api/laps")
        def get_laps():
            """Get list of lap markers."""
            return jsonify({
                "laps": self.session_data.lap_markers
            })

        @self.app.route("/api/chart/timeseries")
        def chart_timeseries():
            """Get time-series telemetry data for charting."""
            from flask import request

            # Get query parameters
            lap_num = request.args.get("lap", type=int)
            start_time = request.args.get("start_time", type=float)
            end_time = request.args.get("end_time", type=float)

            # Get telemetry range
            samples = self.session_data.get_telemetry_range(
                start_time=start_time,
                end_time=end_time,
                lap_num=lap_num
            )

            if not samples:
                return jsonify({
                    "elapsed": [],
                    "speed": [],
                    "rpm": [],
                    "coolant": [],
                    "throttle": [],
                    "drs_regions": [],
                    "lap_markers": []
                })

            # Extract data arrays
            elapsed = [s.get('elapsed', 0) for s in samples]
            speed = [s.get('speed_kph', 0) for s in samples]
            rpm = [s.get('rpm', 0) for s in samples]
            coolant = [s.get('coolant_temp', 0) for s in samples]
            throttle = [s.get('throttle', 0) for s in samples]

            # Find DRS active regions
            drs_regions = []
            drs_start = None
            for i, s in enumerate(samples):
                if s.get('drs_active'):
                    if drs_start is None:
                        drs_start = s.get('elapsed', 0)
                else:
                    if drs_start is not None:
                        drs_regions.append([drs_start, samples[i-1].get('elapsed', 0)])
                        drs_start = None

            # Close final DRS region if still active
            if drs_start is not None and samples:
                drs_regions.append([drs_start, samples[-1].get('elapsed', 0)])

            # Get lap markers in range
            markers_in_range = []
            for marker in self.session_data.lap_markers:
                marker_elapsed = marker.get('elapsed', 0)
                if start_time is not None and marker.get('timestamp', 0) < start_time:
                    continue
                if end_time is not None and marker.get('timestamp', 0) > end_time:
                    continue
                markers_in_range.append(marker_elapsed)

            return jsonify({
                "elapsed": elapsed,
                "speed": speed,
                "rpm": rpm,
                "coolant": coolant,
                "throttle": throttle,
                "drs_regions": drs_regions,
                "lap_markers": markers_in_range
            })

        @self.app.route("/export/csv")
        def export_csv():
            """Export all telemetry data as CSV with lap markers."""
            if not self.session_data.telemetry:
                return "No data available", 404

            # Build CSV with telemetry + lap marker rows
            lines = ["timestamp,elapsed_seconds,speed_kph,rpm,coolant_temp,throttle_pct,drs_active,brake,lap"]

            for sample in self.session_data.telemetry:
                lines.append(
                    f"{sample.get('timestamp', 0):.3f},"
                    f"{sample.get('elapsed', 0):.2f},"
                    f"{sample.get('speed_kph', 0):.1f},"
                    f"{sample.get('rpm', 0):.0f},"
                    f"{sample.get('coolant_temp', 0):.1f},"
                    f"{sample.get('throttle', 0):.1f},"
                    f"{sample.get('drs_active', False)},"
                    f"{sample.get('brake', False)},"
                    f"{sample.get('lap', 1)}"
                )

                # Insert lap marker comment after the marker timestamp
                for marker in self.session_data.lap_markers:
                    if abs(marker['timestamp'] - sample.get('timestamp', 0)) < 0.001:
                        note = f" - {marker['note']}" if marker['note'] else ""
                        lines.append(f"# LAP MARKER: Lap {marker['lap_num']} Complete - {marker['elapsed']:.2f}s{note}")

            csv_data = "\n".join(lines)

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=telemetry_session.csv"}
            )

    def run(self, host="0.0.0.0", port=5000, debug=False):
        """Run Flask server."""
        self.app.run(host=host, port=port, debug=debug, threaded=True)

