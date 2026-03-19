from datetime import datetime
from typing import List, Optional, Union

from domain.runnerSession import RunnerSession
from domain.workoutState import WorkoutState
from domain.runnerState import RunnerState


class Workout:
    """
    Domain Entity: Workout
    """

    #changed the constructor to include startMode as an optional parameter, and added validation for intervalDistance and lapsPerInterval. Also added helper functions to find runner sessions by NFC and RFID tags, and a function to get the rest screen data for display purposes.

    def __init__(
        self,
        workout_id: int,
        intervalDistance: int,
        lapsPerInterval: int,
        startMode: str,
        status: Optional[Union[WorkoutState, str]] = None,
        runnerSessions: Optional[List[RunnerSession]] = None,
        startTime: Optional[str] = None,
        endTime: Optional[str] = None,
    ):
        self.workout_id = workout_id
        self.intervalDistance = intervalDistance
        self.lapsPerInterval = lapsPerInterval
        self.startMode = startMode

        # status is now an enum (accept string for loading)
        if status is None:
            self.status: WorkoutState = WorkoutState.NOT_STARTED
        elif isinstance(status, WorkoutState):
            self.status = status
        else:
            self.status = WorkoutState(status)

        self.runnerSessions = [] if runnerSessions is None else runnerSessions
        self.startTime = startTime
        self.endTime = endTime

        self._validate_config()

    # ---------------------------
    # Domain Behavior
    # ---------------------------

    def start(self) -> bool:
        """Coach activates workout, system begins accepting NFC/RFID events."""
        if self.status != WorkoutState.NOT_STARTED:
            return False
        self.status = WorkoutState.ACTIVE
        self.startTime = datetime.now().isoformat()
        return True

    def end(self) -> bool:
        """Workout ended by coach, finalize sessions."""
        if self.status == WorkoutState.COMPLETED:
            return False
        self.status = WorkoutState.COMPLETED
        self.endTime = datetime.now().isoformat()
        return True

    def add_runner_session(self, rs: RunnerSession) -> bool:
        if self.status != WorkoutState.NOT_STARTED:
            return False
        self.runnerSessions.append(rs)
        return True

    def record_nfc_start(self, nfc_tag: str) -> None:
        """Runner scans NFC to start an interval."""
        if self.status != WorkoutState.ACTIVE:
            raise ValueError("Workout is not active")

        rs = self._find_runner_session_by_nfc(nfc_tag)
        if rs is None:
            raise ValueError("Unknown NFC tag")

        rs.start_interval()

    def record_rfid_event(self, rfid_tag: str) -> RunnerState:
        """
        RFID detection while running.
        RunnerSession owns the finish logic now.
        """
        if self.status != WorkoutState.ACTIVE:
            raise ValueError("Workout is not active (cannot accept events)")

        rs = self._find_runner_session_by_rfid(rfid_tag)
        if rs is None:
            raise ValueError("Unknown RFID tag")

        # moved finish orchestration into session
        return rs.record_lap_and_update_state(self.lapsPerInterval)

    def get_rest_screen(self) -> List[dict]:
        """
        Display helper.
        Note: your professor said "remaining rest" should be UI-side,
        but keeping it for now since your CLI uses it.
        """
        if self.status != WorkoutState.ACTIVE:
            return []

        rows = []
        for rs in self.runnerSessions:
            rs.check_if_ready()
            if rs.state == RunnerState.RESTING:
                rows.append({
                    "runner_id": rs.runner.id,
                    "runner_name": rs.runner.name,
                    "remaining_seconds": rs.get_remaining_restDuration(),
                    "state": rs.state.value,  # return string for display
                })

        rows.sort(key=lambda x: x["remaining_seconds"])
        return rows

    def get_runner_counts(self) -> tuple:
        """Returns active (RUNNING) and resting runner counts."""
        active_count = sum(1 for rs in self.runnerSessions if rs.state == RunnerState.RUNNING)
        resting_count = sum(1 for rs in self.runnerSessions if rs.state == RunnerState.RESTING)
        return active_count, resting_count
    
    def get_resting_runner_sessions(self) -> List[RunnerSession]:
        """
        Returns all runner sessions currently resting.
        Domain decides eligibility.
        """
        if self.status != WorkoutState.ACTIVE:
            return []

        resting = []

        for rs in self.runnerSessions:
            rs.check_if_ready()

            if rs.state == RunnerState.RESTING:
                resting.append(rs)

        return resting

    # ---------------------------
    # Helper functions
    # ---------------------------

    def _find_runner_session_by_rfid(self, rfid_tag: str) -> Optional[RunnerSession]:
        for rs in self.runnerSessions:
            if rs.runner.rfid_tag == rfid_tag:
                return rs
        return None

    def _find_runner_session_by_nfc(self, nfc_tag: str) -> Optional[RunnerSession]:
        for rs in self.runnerSessions:
            if rs.runner.nfc_tag == nfc_tag:
                return rs
        return None

    def _validate_config(self) -> None:
        if self.intervalDistance <= 0:
            raise ValueError("Interval distance must be positive")
        if self.lapsPerInterval < 1:
            raise ValueError("Must have at least 1 lap per interval")

    # ---------------------------
    # Persistence helpers
    # ---------------------------

    def to_dict(self) -> dict:
        return {
            "workout_id": self.workout_id,
            "intervalDistance": self.intervalDistance,
            "lapsPerInterval": self.lapsPerInterval,
            "startMode": self.startMode,
            "status": self.status.value,  # store as string
            "startTime": self.startTime,
            "endTime": self.endTime,
            "runnerSessions": [rs.to_dict() for rs in self.runnerSessions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workout":
        from domain.runnerSession import RunnerSession
        return cls(
            workout_id=data["workout_id"],
            intervalDistance=data["intervalDistance"],
            lapsPerInterval=data["lapsPerInterval"],
            startMode=data.get("startMode", "INDIVIDUAL"),
            status=data.get("status"),  # string -> converted in __init__
            runnerSessions=[RunnerSession.from_dict(x) for x in data.get("runnerSessions", [])],
            startTime=data.get("startTime"),
            endTime=data.get("endTime"),
        )