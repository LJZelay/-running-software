from datetime import datetime
from typing import List, Optional
from domain.runner import Runner
"""from datetime import datetime"""

"""def _parse_ts(ts: str) -> datetime:
    "return datetime.fromisoformat(ts)"""

class RunnerSession:
    """
    Domain Entity: RunnerSession

    Stores dynamic state of a runner during a workout session:
    - runner identity
    - restDuration (dynamic)
    - current state (NOT_STARTED / READY / RUNNING / RESTING)
    - interval timestamps
    - rest timestamps

    Core rules:
    - cannot start if already running
    - cannot start if resting
    - rest expires after restDuration, then state becomes READY
    - interval finishes when laps_per_interval is reached, then rest starts immediately
    """

    def __init__(
        self,
        runner: Runner,
        restDuration: int,
        state: Optional[str] = None,
        intervals: Optional[List[dict]] = None,
        rests: Optional[List[dict]] = None,
    ):
        self.runner = runner
        self.restDuration = restDuration

        self.state = "NOT_STARTED" if state is None else state
        self.intervals = [] if intervals is None else intervals
        self.rests = [] if rests is None else rests

    # ---------------------------
    # Domain Behavior
    # ---------------------------

    def start_interval(self):
        """
        Start running an interval when NFC scan occurs.
        """
        self.check_if_ready()

        if self.state == "RUNNING":
            raise ValueError("Runner is already running")
        if self.state == "RESTING":
            raise ValueError("Runner is resting and cannot start yet")

        intervalNumber = len(self.intervals) + 1
        self.intervals.append({
            "intervalNumber": intervalNumber,
            "start": datetime.now().isoformat(),
            "laps": [],
            "end": None
        })
        self.state = "RUNNING"

    def record_lap(self):
        """
        Record an RFID detection (a lap completion) while running.
        """
        if self.state != "RUNNING":
            raise ValueError("Cannot record lap unless runner is running")
        currentInterval = self.intervals[-1]
        currentInterval["laps"].append(datetime.now().isoformat())

    def should_finish_interval(self, lapsPerInterval: int) -> bool:
        """
        Check if current interval is complete based on number of laps.
        """
        if self.state != "RUNNING":
            return False
        currentInterval = self.intervals[-1]
        return len(currentInterval["laps"]) >= lapsPerInterval

    def finish_interval(self):
        """
        Finish current running interval and start rest.
        """
        if self.state != "RUNNING":
            raise ValueError("Runner is not running")

        currentInterval = self.intervals[-1]
        currentInterval["end"] = datetime.now().isoformat()

        self.rests.append({
            "start": datetime.now().isoformat(),
            "restDuration": self.restDuration,
            "end": None
        })
        self.state = "RESTING"

    def check_if_ready(self):
        """
        Check if runner is ready to start a new interval (rest period over).
        """
        if self.state != "RESTING":
            return

        currentRest = self.rests[-1]
        startTime = datetime.fromisoformat(currentRest["start"])
        elapsed = (datetime.now() - startTime).total_seconds()

        if elapsed >= currentRest["restDuration"]:
            if currentRest["end"] is None:
                currentRest["end"] = datetime.now().isoformat()
            self.state = "READY"

    def get_remaining_restDuration(self) -> int:
        """
        For display purposes
        """
        if self.state != "RESTING":
            return 0

        currentRest = self.rests[-1]
        startTime = datetime.fromisoformat(currentRest["start"])
        elapsed = (datetime.now() - startTime).total_seconds()
        remaining = currentRest["restDuration"] - int(elapsed)
        return max(0, remaining)

    # ---------------------------
    # Persistence helpers
    # ---------------------------

    def to_dict(self):
        return {
            "runner": self.runner.to_dict(),
            "restDuration": self.restDuration,
            "state": self.state,
            "intervals": self.intervals,
            "rests": self.rests,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            runner=Runner.from_dict(data["runner"]),
            restDuration=data["restDuration"],
            state=data.get("state"),
            intervals=data.get("intervals"),
            rests=data.get("rests"),
        )
