"""Flask dashboard for real-time telemetry visualization."""

from pathlib import Path
from typing import TYPE_CHECKING

from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO, emit
import time
from threading import Thread

if TYPE_CHECKING:
    from apps.telemetry.main import TelemetryApp

app = Flask(__name__)
app.config["SECRET_KEY"] = "lemons-telemetry-secret"
socketio = SocketIO(app, cors_allowed_origins="*")

telemetry_app_instance = None


@app.route("/")
def index():
    """Serve main dashboard page."""
    # For now, serve embedded HTML (later move to web/telemetry/)
    html_path = Path(__file__).parent.parent.parent / "web" / "telemetry" / "index.html"

    if html_path.exists():
        with open(html_path) as f:
            return f.read()
    else:
        # Fallback: simple embedded dashboard
        return render_template_string(SIMPLE_DASHBOARD_HTML)


@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    """Get current telemetry data (REST endpoint)."""
    if telemetry_app_instance is None:
        return jsonify({"error": "Telemetry app not initialized"}), 500

    data = telemetry_app_instance.get_telemetry_data()
    return jsonify(data)


@app.route("/healthz", methods=["GET"])
def healthz():
    """Health check endpoint for monitoring."""
    if telemetry_app_instance is None:
        return jsonify({"status": "error", "reason": "Not initialized"}), 503

    health = telemetry_app_instance.health.get_status()

    if health["status"] in ["healthy", "degraded"]:
        return jsonify(health), 200
    else:
        return jsonify(health), 503


@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection."""
    print("Client connected to telemetry stream")
    emit("status", {"message": "Connected to telemetry"})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket disconnection."""
    print("Client disconnected from telemetry stream")


def broadcast_telemetry():
    """Background thread to broadcast telemetry data via WebSocket."""
    while True:
        if telemetry_app_instance:
            data = telemetry_app_instance.get_telemetry_data()
            socketio.emit("telemetry_update", data)
        time.sleep(0.5)  # Update at 2 Hz


def start_dashboard_server(
    telemetry_app: "TelemetryApp", port: int = 5000, bind: str = "0.0.0.0"
):
    """
    Start Flask dashboard server with WebSocket support.

    Args:
        telemetry_app: Telemetry app instance to query
        port: Port to bind to
        bind: Address to bind to
    """
    global telemetry_app_instance
    telemetry_app_instance = telemetry_app

    # Start background broadcast thread
    broadcast_thread = Thread(target=broadcast_telemetry, daemon=True)
    broadcast_thread.start()

    # Disable Flask's default logging (use our logger)
    import logging

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    telemetry_app.logger.info(f"Starting dashboard server on {bind}:{port}")
    socketio.run(app, host=bind, port=port, debug=False, use_reloader=False)


# Simple embedded dashboard HTML (fallback if web/telemetry/index.html doesn't exist)
SIMPLE_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>24 Hours of Lemons - Telemetry</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body { font-family: monospace; background: #000; color: #0f0; padding: 20px; }
        .metric { font-size: 24px; margin: 10px 0; }
        .label { color: #888; }
        .value { color: #0f0; font-weight: bold; }
        .drs-active { color: #ff0; }
        .header { font-size: 32px; margin-bottom: 20px; border-bottom: 2px solid #0f0; }
    </style>
</head>
<body>
    <div class="header">🏁 24 Hours of Lemons - Live Telemetry</div>
    <div class="metric"><span class="label">Speed:</span> <span id="speed" class="value">--</span> km/h</div>
    <div class="metric"><span class="label">RPM:</span> <span id="rpm" class="value">--</span></div>
    <div class="metric"><span class="label">Coolant Temp:</span> <span id="coolant" class="value">--</span> °C</div>
    <div class="metric"><span class="label">DRS Status:</span> <span id="drs" class="value">--</span></div>
    <div class="metric"><span class="label">Connection:</span> <span id="status" class="value">Connecting...</span></div>

    <script>
        const socket = io();

        socket.on('connect', () => {
            document.getElementById('status').textContent = 'Connected';
        });

        socket.on('disconnect', () => {
            document.getElementById('status').textContent = 'Disconnected';
        });

        socket.on('telemetry_update', (data) => {
            // OBD data
            if (data.obd) {
                document.getElementById('speed').textContent = data.obd.SPEED?.toFixed(1) || '--';
                document.getElementById('rpm').textContent = data.obd.RPM?.toFixed(0) || '--';
                document.getElementById('coolant').textContent = data.obd.COOLANT_TEMP?.toFixed(1) || '--';
            }

            // DRS status
            if (data.custom && data.custom.drs) {
                const drsElement = document.getElementById('drs');
                const drsActive = data.custom.drs.active;
                drsElement.textContent = drsActive ? 'ACTIVE' : 'IDLE';
                drsElement.className = drsActive ? 'value drs-active' : 'value';
            }
        });
    </script>
</body>
</html>
"""
