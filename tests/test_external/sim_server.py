"""
RFID Simulation Server
Mimics an Impinj REST reader for local testing.

Endpoints:
  POST /api/v1/profiles/stop
  POST /api/v1/profiles/inventory/presets/default/start
  GET  /api/v1/data/stream   (newline-delimited JSON stream)

Usage:
  pip install flask
  python rfid_sim_server.py

Config (env vars):
  RFID_SIM_HOST      bind host   (default: 0.0.0.0)
  RFID_SIM_PORT      bind port   (default: 5000)
  RFID_SIM_INTERVAL  seconds between tag events (default: 2.0)
"""

import base64
import json
import os
import random
import time
from datetime import datetime, timezone

from flask import Flask, Response, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A small pool of realistic-looking 96-bit EPCs (12 bytes each)
SAMPLE_EPCS_HEX = [
    "300833B2DDD9014000000001",
    "300833B2DDD9014000000002",
    "300833B2DDD9014000000003",
    "300833B2DDD9014000000004",
    "E28011606000020520A0614E",
    "E2801160600002050000000A",
]


def hex_to_base64(hex_str: str) -> str:
    """Convert a hex EPC string to the base64 encoding the reader sends."""
    return base64.b64encode(bytes.fromhex(hex_str)).decode("ascii")


def make_tag_event(epc_hex: str | None = None) -> dict:
    """Build one tagInventoryEvent payload."""
    epc_hex = epc_hex or random.choice(SAMPLE_EPCS_HEX)
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "tagInventoryEvent": {
            "epc": hex_to_base64(epc_hex),
            "antennaPort": random.randint(1, 4),
            "peakRssiCdbm": random.randint(-800, -400),
        },
    }


# ---------------------------------------------------------------------------
# Control endpoints
# ---------------------------------------------------------------------------

@app.route("/api/v1/profiles/stop", methods=["POST"])
def profiles_stop():
    app.logger.info("▶ profiles/stop called")
    return jsonify({"status": "stopped"}), 200


@app.route("/api/v1/profiles/inventory/presets/default/start", methods=["POST"])
def profiles_start():
    app.logger.info("▶ profiles/inventory/presets/default/start called")
    return jsonify({"status": "started"}), 200


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------

INTERVAL = float(os.getenv("RFID_SIM_INTERVAL", "2.0"))


def event_generator():
    """Yield newline-delimited JSON tag events indefinitely."""
    app.logger.info("📡 Stream client connected")
    try:
        while True:
            payload = make_tag_event()
            line = json.dumps(payload) + "\n"
            app.logger.debug("  → %s", line.strip())
            yield line.encode("utf-8")
            time.sleep(INTERVAL)
    except GeneratorExit:
        app.logger.info("📡 Stream client disconnected")


@app.route("/api/v1/data/stream", methods=["GET"])
def data_stream():
    return Response(
        event_generator(),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if behind proxy
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("RFID_SIM_HOST", "0.0.0.0")
    port = int(os.getenv("RFID_SIM_PORT", "5001"))

    # Use threaded=True so the streaming response doesn't block control calls
    app.run(host=host, port=port, threaded=True, debug=True)
