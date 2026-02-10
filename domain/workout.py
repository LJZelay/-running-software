from datetime import datetime
from typing import List, Optional
from domain.runnerSession import RunnerSession


class Workout:
    """
    Domain Entity: Workout

    Contains:
    - shared workout configs
    - list of RunnerSession objects (per-runner dynamic states and info+configs)
    - status/lifecycle (NOT_STARTED / ACTIVE / COMPLETED)

    Design decision:
    - Coach activates the workout (start()).
    - Every runner starts their interval only by NFC scan (record_nfc_start()).
    """

    def __init__(
        self,
        workout_id: int,
        intervalDistance: int,
        lapsPerInterval: int,
        startMode: str,  # you can keep this for now or remove it entirely
        status: Optional[str] = None,
        runnerSessions: Optional[List[RunnerSession]] = None,
        startTime: Optional[str] = None,
        endTime: Optional[str] = None,
    ):
        self.workout_id = workout_id
        self.intervalDistance = intervalDistance
        self.lapsPerInterval = lapsPerInterval
        self.startMode = startMode  # optional now

        self.status = "NOT_STARTED" if status is None else status
        self.runnerSessions = [] if runnerSessions is None else runnerSessions

        self.startTime = startTime
        self.endTime = endTime

        self._validate_config()

    # ---------------------------
    # Domain Behavior
    # ---------------------------

    def start(self) -> bool:
        """Coach activates workout, system begins accepting NFC/RFID events."""
        if self.status != "NOT_STARTED":
            return False
        self.status = "ACTIVE"
        self.startTime = datetime.now().isoformat()
        return True

    def end(self) -> bool:
        """Workout ended by coach, finalize sessions"""
        if self.status == "COMPLETED":
            return False
        self.status = "COMPLETED"
        self.endTime = datetime.now().isoformat()
        return True

    def add_runner_session(self, rs: RunnerSession) -> bool:
        if self.status != "NOT_STARTED":
            return False
        self.runnerSessions.append(rs)
        return True

    def record_nfc_start(self, nfc_tag: str):
        """
        Runner scans NFC to start an interval.
        """
        if self.status != "ACTIVE":
            raise ValueError("Workout is not active")

        rs = self._find_runner_session_by_nfc(nfc_tag)
        if rs is None:
            raise ValueError("Unknown NFC tag")

        rs.start_interval()

    def record_rfid_event(self, rfid_tag: str):
        """
        RFID detection while running.
        - Records a lap
        - If lap threshold reached, finishes interval and starts rest immediately
        """
        if self.status != "ACTIVE":
            raise ValueError("Workout is not active (cannot accept events)")

        rs = self._find_runner_session_by_rfid(rfid_tag)
        if rs is None:
            raise ValueError("Unknown RFID tag")

        rs.record_lap()

        if rs.should_finish_interval(self.lapsPerInterval):
            rs.finish_interval()

    def get_rest_screen(self) -> List[dict]:
        """
        For display purposes
        """
        if self.status != "ACTIVE":
            return []

        rows = []
        for rs in self.runnerSessions:
            rs.check_if_ready()
            if rs.state == "RESTING":
                rows.append({
                    "runner_id": rs.runner.id,
                    "runner_name": rs.runner.name,
                    "remaining_seconds": rs.get_remaining_restDuration(),
                    "state": rs.state
                })

        rows.sort(key=lambda x: x["remaining_seconds"])
        return rows

    def get_runner_counts(self) -> tuple:
        """
        Returns active and resting runner counts
        """
        active_count = sum(1 for rs in self.runnerSessions if rs.state == "RUNNING")
        resting_count = sum(1 for rs in self.runnerSessions if rs.state == "RESTING")
        return active_count, resting_count

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

    def _validate_config(self):
        if self.intervalDistance <= 0:
            raise ValueError("Interval distance must be positive")
        if self.lapsPerInterval < 1:
            raise ValueError("Must have at least 1 lap per interval")

    # ---------------------------
    # Persistence helpers
    # ---------------------------

    def to_dict(self):
        return {
            "workout_id": self.workout_id,
            "intervalDistance": self.intervalDistance,
            "lapsPerInterval": self.lapsPerInterval,
            "startMode": self.startMode,
            "status": self.status,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "runnerSessions": [rs.to_dict() for rs in self.runnerSessions],
        }

    @classmethod
    def from_dict(cls, data):
        from domain.runnerSession import RunnerSession
        return cls(
            workout_id=data["workout_id"],
            intervalDistance=data["intervalDistance"],
            lapsPerInterval=data["lapsPerInterval"],
            startMode=data.get("startMode", "INDIVIDUAL"),
            status=data.get("status"),
            runnerSessions=[RunnerSession.from_dict(x) for x in data.get("runnerSessions", [])],
            startTime=data.get("startTime"),
            endTime=data.get("endTime"),
        )
