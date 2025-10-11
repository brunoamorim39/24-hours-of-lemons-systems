"""Flask API for DRS status monitoring."""

from typing import TYPE_CHECKING

from flask import Flask, jsonify

if TYPE_CHECKING:
    from apps.drs.main import DRSApp

app = Flask(__name__)
drs_app_instance = None


@app.route("/status", methods=["GET"])
def get_status():
    """Get current DRS status."""
    if drs_app_instance is None:
        return jsonify({"error": "DRS app not initialized"}), 500

    status = drs_app_instance.get_status()
    return jsonify(status)


@app.route("/healthz", methods=["GET"])
def healthz():
    """Health check endpoint for monitoring."""
    if drs_app_instance is None:
        return jsonify({"status": "error", "reason": "Not initialized"}), 503

    health = drs_app_instance.health.get_status()

    if health["status"] == "healthy":
        return jsonify(health), 200
    elif health["status"] == "degraded":
        return jsonify(health), 200
    else:
        return jsonify(health), 503


def start_api_server(drs_app: "DRSApp", port: int = 5001, bind: str = "0.0.0.0"):
    """
    Start Flask API server.

    Args:
        drs_app: DRS app instance to query
        port: Port to bind to
        bind: Address to bind to
    """
    global drs_app_instance
    drs_app_instance = drs_app

    # Disable Flask's default logging (use our logger)
    import logging

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    drs_app.logger.info(f"Starting API server on {bind}:{port}")
    app.run(host=bind, port=port, debug=False, use_reloader=False)
