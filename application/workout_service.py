from typing import Dict, List, Optional
from application.WorkoutConfig import WorkoutConfig
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.runnerState import RunnerState


class WorkoutService:
    """
    Application-layer coordinator (use-case-ish).
    Does NOT read files.
    Accepts parsed data from controllers/external_interfaces.
    """

    def __init__(self, config: Optional[WorkoutConfig] = None) -> None:
        self.config = config or WorkoutConfig()

        self.interval_distance = self.config.interval_distance
        self.rest_time_seconds = self.config.rest_time_seconds
        self.laps_per_interval = self.config.laps_per_interval

        self.athletes_by_nfc: Dict[str, RunnerSession] = {}
        self.athletes_by_rfid: Dict[str, RunnerSession] = {}
        self.current_group: List[RunnerSession] = []
        self.is_terminated = False

    # -------------------------
    # Registration
    # -------------------------

    def register_runners(self, runners: List[Runner]) -> int:
        """
        Add runners to the system (e.g. after CSV parsing in outer layer).
        Returns number added.
        """
        self._ensure_active()

        for runner in runners:
            nfc_tag = runner.nfc_tag
            rfid_tag = runner.rfid_tag

            if nfc_tag in self.athletes_by_nfc:
                raise ValueError(f"Duplicate NFC tag: {nfc_tag}")
            if rfid_tag in self.athletes_by_rfid:
                raise ValueError(f"Duplicate RFID tag: {rfid_tag}")

            session = RunnerSession(runner=runner, restDuration=self.rest_time_seconds)
            self.athletes_by_nfc[nfc_tag] = session
            self.athletes_by_rfid[rfid_tag] = session

        return len(runners)

    # -------------------------
    # Group / Start
    # -------------------------

    def add_athlete_to_group(self, nfc_tag: str) -> bool:
        self._ensure_active()
        session = self._get_by_nfc(nfc_tag)
        if session in self.current_group:
            return False
        self.current_group.append(session)
        return True

    def trigger_group_start(self) -> int:
        self._ensure_active()
        if not self.current_group:
            return 0

        for session in self.current_group:
            session.start_interval()

        started_count = len(self.current_group)
        self.current_group.clear()
        return started_count

    # -------------------------
    # Event handling
    # -------------------------

    def handle_rfid_detected(self, rfid_tag: str) -> RunnerState:
        self._ensure_active()
        session = self._get_by_rfid(rfid_tag)
        return session.record_lap_and_update_state(self.laps_per_interval)

    def handle_nfc_scanned(self, nfc_tag: str) -> RunnerState:
        self._ensure_active()
        session = self._get_by_nfc(nfc_tag)
        session.start_interval()
        return session.state

    # -------------------------
    # Query functions (return objects, not dicts)
    # -------------------------

    def get_resting_sessions(self) -> List[RunnerSession]:
        """
        Returns RunnerSession objects that are currently RESTING.
        UI can compute remaining rest time using timestamps.
        """
        self._ensure_active()
        resting: List[RunnerSession] = []

        for session in self.athletes_by_nfc.values():
            session.check_if_ready()
            if session.state == RunnerState.RESTING:
                resting.append(session)

        return resting

    def get_running_sessions(self) -> List[RunnerSession]:
        self._ensure_active()
        return [s for s in self.athletes_by_nfc.values() if s.state == RunnerState.RUNNING]

    def terminate_workout(self) -> None:
        self.is_terminated = True
        self.current_group.clear()

    # -------------------------
    # Helpers
    # -------------------------

    def _get_by_nfc(self, nfc_tag: str) -> RunnerSession:
        session = self.athletes_by_nfc.get(nfc_tag)
        if session is None:
            raise ValueError("Unknown NFC tag")
        return session

    def _get_by_rfid(self, rfid_tag: str) -> RunnerSession:
        session = self.athletes_by_rfid.get(rfid_tag)
        if session is None:
            raise ValueError("Unknown RFID tag")
        return session

    def _ensure_active(self) -> None:
        if self.is_terminated:
            raise ValueError("Workout is terminated")