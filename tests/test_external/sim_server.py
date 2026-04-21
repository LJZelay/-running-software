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
    RFID_SIM_PORT      bind port   (default: 5001)
    RFID_SIM_INTERVAL  seconds between RFID lap events (default: 1.5)
    RFID_SIM_HEARTBEAT seconds between keepalive frames (default: 0.4)
    RFID_SIM_LAPS_PER_INTERVAL laps required to complete an interval (default: 4)
    RFID_SIM_REST_SECONDS cooldown after interval completion (default: 8)
    RFID_SIM_TRACK_DISTANCE_M meters per lap for pace metadata (default: 400)
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

# Default tags aligned with team-project-team4/data/athletes.csv
DEFAULT_EPCS_HEX = [
    "74",
    "300833B2DDD9014000000002",
    "300833B2DDD9014000000003",
    "300833B2DDD9014000000004",
    "E28011606000020520A0614E",
    "E2801160600002050000000A",
]

EPCS_HEX = [
    item.strip().upper()
    for item in os.getenv("RFID_SIM_TAGS", ",".join(DEFAULT_EPCS_HEX)).split(",")
    if item.strip()
]
MODE = os.getenv("RFID_SIM_MODE", "round_robin").strip().lower()
INTERVAL = float(os.getenv("RFID_SIM_INTERVAL", "1.5"))
HEARTBEAT_INTERVAL = float(os.getenv("RFID_SIM_HEARTBEAT", "0.4"))
LAPS_PER_INTERVAL = max(1, int(os.getenv("RFID_SIM_LAPS_PER_INTERVAL", "4")))
REST_SECONDS = max(0.0, float(os.getenv("RFID_SIM_REST_SECONDS", "8")))
TRACK_DISTANCE_M = max(1, int(os.getenv("RFID_SIM_TRACK_DISTANCE_M", "400")))

SIM_STATE = {
    tag: {
        "total_laps": 0,
        "interval_laps": 0,
        "completed_intervals": 0,
        "next_eligible_at": 0.0,
        "last_lap_ms": None,
    }
    for tag in EPCS_HEX
}


def hex_to_base64(hex_str: str) -> str:
    """Convert a hex EPC string to the base64 encoding the reader sends."""
    return base64.b64encode(bytes.fromhex(hex_str)).decode("ascii")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _choose_next_tag(last_index: int) -> tuple[str | None, int]:
    """Pick next eligible tag based on mode and cooldown windows."""
    if not EPCS_HEX:
        return None, last_index

    now_s = time.time()
    eligible_indices = [
        i for i, tag in enumerate(EPCS_HEX)
        if SIM_STATE[tag]["next_eligible_at"] <= now_s
    ]
    if not eligible_indices:
        return None, last_index

    if MODE == "random":
        idx = random.choice(eligible_indices)
        return EPCS_HEX[idx], idx

    for step in range(1, len(EPCS_HEX) + 1):
        idx = (last_index + step) % len(EPCS_HEX)
        if idx in eligible_indices:
            return EPCS_HEX[idx], idx

    return None, last_index


def make_tag_event(epc_hex: str) -> dict:
    """Build one tagInventoryEvent payload with extra simulation metadata."""
    state = SIM_STATE[epc_hex]
    now_ms = int(time.time() * 1000)
    simulated_lap_ms = random.randint(68_000, 115_000)
    state["last_lap_ms"] = simulated_lap_ms

    state["total_laps"] += 1
    state["interval_laps"] += 1

    interval_complete = False
    if state["interval_laps"] >= LAPS_PER_INTERVAL:
        interval_complete = True
        state["completed_intervals"] += 1
        state["interval_laps"] = 0
        state["next_eligible_at"] = time.time() + REST_SECONDS

    # Pace metadata for observability; app can ignore unknown fields safely.
    pace_min_per_km = round((simulated_lap_ms / 1000.0) / (TRACK_DISTANCE_M / 1000.0) / 60.0, 2)

    return {
        "timestamp": _now_iso(),
        "tagInventoryEvent": {
            "epc": hex_to_base64(epc_hex),
            "antennaPort": 1,
            "peakRssiCdbm": -600,
        },
        "simMeta": {
            "totalLaps": state["total_laps"],
            "intervalLaps": state["interval_laps"],
            "completedIntervals": state["completed_intervals"],
            "intervalComplete": interval_complete,
            "simulatedLapMs": simulated_lap_ms,
            "simulatedPaceMinPerKm": pace_min_per_km,
            "trackDistanceM": TRACK_DISTANCE_M,
            "lapsPerInterval": LAPS_PER_INTERVAL,
            "restSeconds": REST_SECONDS,
            "eventEpochMs": now_ms,
        },
    }


def make_heartbeat_event() -> dict:
    return {
        "timestamp": _now_iso(),
        "simHeartbeat": True,
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

def event_generator():
    """Yield newline-delimited JSON RFID + heartbeat events indefinitely."""
    app.logger.info("📡 Stream client connected")
    index = -1
    next_tag_at = time.time()
    next_heartbeat_at = time.time()
    try:
        while True:
            now = time.time()

            if now >= next_tag_at:
                tag, index = _choose_next_tag(index)
                if tag is not None:
                    payload = make_tag_event(tag)
                    line = json.dumps(payload) + "\n"
                    app.logger.debug("  → RFID %s", line.strip())
                    yield line.encode("utf-8")
                next_tag_at = now + INTERVAL

            if now >= next_heartbeat_at:
                heartbeat = make_heartbeat_event()
                line = json.dumps(heartbeat) + "\n"
                yield line.encode("utf-8")
                next_heartbeat_at = now + HEARTBEAT_INTERVAL

            time.sleep(0.05)
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

