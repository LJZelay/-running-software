from datetime import datetime
from typing import List, Optional, Any, Dict, Union
from domain.runner import Runner
from domain.runnerState import RunnerState

"""def _parse_ts(ts: str) -> datetime:
    "return datetime.fromisoformat(ts)"""

class RunnerSession:
    """
    Domain Entity: RunnerSession

    Stores dynamic state of a runner during a workout session:
    - runner identity
    - restDuration (per-runner)
    - current state (RunnerState)
    - interval timestamps
    - rest timestamps

    Core rules:
    - cannot start if already running
    - cannot start if resting (unless rest expired -> READY)
    - rest expires after restDuration, then state becomes READY
    - interval finishes when laps_per_interval is reached, then rest starts immediately
    """

    def __init__(
        self,
        runner: Runner,
        restDuration: int,
        state: Optional[Union[RunnerState, str]] = None,
        intervals: Optional[List[Dict[str, Any]]] = None,
        rests: Optional[List[Dict[str, Any]]] = None,
    ):
        self.runner = runner
        self.restDuration = restDuration

        # Convert incoming state (string or enum) into RunnerState
        if state is None:
            self.state: RunnerState = RunnerState.NOT_STARTED
        elif isinstance(state, RunnerState):
            self.state = state
        else:
            # Expect strings like "NOT_STARTED", "READY", "RUNNING", "RESTING"
            self.state = RunnerState(state)

        self.intervals = [] if intervals is None else intervals
        self.rests = [] if rests is None else rests

    # ---------------------------
    # Domain Behavior
    # ---------------------------

    def start_interval(self) -> None:
        """
        Start running an interval when NFC scan occurs.
        """
        self.check_if_ready()

        if self.state == RunnerState.RUNNING:
            raise ValueError("Runner is already running")
        if self.state == RunnerState.RESTING:
            raise ValueError("Runner is resting and cannot start yet")

        intervalNumber = len(self.intervals) + 1
        self.intervals.append({
            "intervalNumber": intervalNumber,
            "start": datetime.now().isoformat(),
            "laps": [],
            "end": None
        })
        self.state = RunnerState.RUNNING

    def record_lap(self) -> None:
        """
        Record an RFID detection (a lap completion) while running.
        """
        if self.state != RunnerState.RUNNING:
            raise ValueError("Cannot record lap unless runner is running")
        currentInterval = self.intervals[-1]
        currentInterval["laps"].append(datetime.now().isoformat())

    def should_finish_interval(self, lapsPerInterval: int) -> bool:
        """
        Check if current interval is complete based on number of laps.
        """
        if self.state != RunnerState.RUNNING:
            return False
        currentInterval = self.intervals[-1]
        return len(currentInterval["laps"]) >= lapsPerInterval

    def record_lap_and_update_state(self, lapsPerInterval: int) -> RunnerState:
        """
        Convenience method so application layer doesn't need to orchestrate finish logic.
        """
        self.record_lap()
        if self.should_finish_interval(lapsPerInterval):
            self.finish_interval()
        return self.state

    def finish_interval(self) -> None:
        """
        Finish current running interval and start rest.
        """
        if self.state != RunnerState.RUNNING:
            raise ValueError("Runner is not running")

        now_iso = datetime.now().isoformat()

        currentInterval = self.intervals[-1]
        currentInterval["end"] = now_iso

        self.rests.append({
            "start": now_iso,
            "restDuration": self.restDuration,
            "end": None
        })
        self.state = RunnerState.RESTING

    def check_if_ready(self) -> None:
        """
        Check if runner is ready to start a new interval (rest period over).
        """
        if self.state != RunnerState.RESTING:
            return

        currentRest = self.rests[-1]
        startTime = datetime.fromisoformat(currentRest["start"])
        elapsed = (datetime.now() - startTime).total_seconds()

        if elapsed >= currentRest["restDuration"]:
            if currentRest["end"] is None:
                currentRest["end"] = datetime.now().isoformat()
            self.state = RunnerState.READY

    # UI concern, might remove later
    def get_remaining_rest_seconds(self, now: Optional[str] = None) -> int:
        """
        Remaining rest seconds
        """
        if self.state != RunnerState.RESTING:
            return 0

        currentRest = self.rests[-1]
        startTime = datetime.fromisoformat(currentRest["start"])
        now_dt = datetime.fromisoformat(now) if now is not None else datetime.now()
        elapsed = (now_dt - startTime).total_seconds()

        remaining = int(currentRest["restDuration"] - elapsed)
        return max(0, remaining)
    
    def is_ready(self) -> bool:
        """
        Returns True if runner is ready to start next interval.
        """
        self.check_if_ready()
        return self.state == RunnerState.READY

    # ---------------------------
    # Persistence helpers
    # ---------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runner": self.runner.to_dict(),
            "restDuration": self.restDuration,
            "state": self.state.value, 
            "intervals": self.intervals,
            "rests": self.rests,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerSession":
        return cls(
            runner=Runner.from_dict(data["runner"]),
            restDuration=data["restDuration"],
            state=data.get("state"),
            intervals=data.get("intervals"),
            rests=data.get("rests"),
        )