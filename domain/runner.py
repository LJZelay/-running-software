# domain/runner.py
from datetime import datetime
from typing import List, Optional


class Runner:
    """
    Domain Entity: Runner

    This class enforces core business rules:
    - Cannot start if already running
    - Cannot be in two states at once
    - Rest begins immediately after interval finishes
    """

    def __init__(
        self,
        runner_id: int,
        name: str,
        nfc_tag: str,
        rfid_tag: str,
        state: Optional[str] = None,
        intervals: Optional[List[dict]] = None,
        rests: Optional[List[dict]] = None,
    ):
        self.id = runner_id
        self.name = name
        self.nfc_tag = nfc_tag
        self.rfid_tag = rfid_tag

        self.state = "NOT_STARTED" if state is None else state
        self.intervals = [] if intervals is None else intervals
        self.rests = [] if rests is None else rests

    # ---------------------------
    # Domain Behavior
    # ---------------------------

    def start_interval(self):
        """Runner starts running."""
        if self.state == "RUNNING":
            raise ValueError("Runner is already running")
        if self.state == "RESTING":
            raise ValueError("Runner is resting and cannot start yet")

        interval_number = len(self.intervals) + 1
        self.intervals.append({
            "interval_number": interval_number,
            "start": datetime.now(),
            "laps": [],
            "end": None
        })

        self.state = "RUNNING"

    def record_lap(self):
        """RFID detection while running."""
        if self.state != "RUNNING":
            raise ValueError("Cannot record lap unless runner is running")

        current_interval = self.intervals[-1]
        current_interval["laps"].append(datetime.now())

    def finish_interval(self, rest_seconds: int):
        """Finish running interval and start rest immediately."""
        if self.state != "RUNNING":
            raise ValueError("Runner is not running")

        current_interval = self.intervals[-1]
        current_interval["end"] = datetime.now()

        # Start rest
        self.rests.append({
            "start": datetime.now(),
            "rest_seconds": rest_seconds,
            "end": None
        })

        self.state = "RESTING"

    def check_if_ready(self):
        """Checks if rest is over and runner can run again."""
        if self.state != "RESTING":
            return

        current_rest = self.rests[-1]
        elapsed = (datetime.now() - current_rest["start"]).total_seconds()

        if elapsed >= current_rest["rest_seconds"]:
            current_rest["end"] = datetime.now()
            self.state = "READY"

    # ---------------------------
    # Persistence helpers
    # ---------------------------

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "nfc_tag": self.nfc_tag,
            "rfid_tag": self.rfid_tag,
            "state": self.state,
            "intervals": self.intervals,
            "rests": self.rests
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            runner_id=data["id"],
            name=data["name"],
            nfc_tag=data["nfc_tag"],
            rfid_tag=data["rfid_tag"],
            state=data["state"],
            intervals=data["intervals"],
            rests=data["rests"]
        )
