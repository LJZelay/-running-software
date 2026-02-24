import csv
from typing import Dict, List, Optional

from application.WorkoutConfig import WorkoutConfig
from domain.runner import Runner
from domain.runnerSession import RunnerSession


class WorkoutService:
    def __init__(self, config: Optional[WorkoutConfig] = None) -> None:
        self.config = config or WorkoutConfig()
        self.interval_distance = self.config.interval_distance
        self.rest_time_seconds = self.config.rest_time_seconds
        self.laps_per_interval = self.config.laps_per_interval

        self.athletes_by_nfc: Dict[str, RunnerSession] = {}
        self.athletes_by_rfid: Dict[str, RunnerSession] = {}
        self.current_group: List[RunnerSession] = []
        self.is_terminated = False

    def load_athletes_from_csv(self, file_path: str) -> int:
        self._ensure_active()
        rows = self._read_csv_rows(file_path)
        runner_id = len(self.athletes_by_nfc) + 1

        for row in rows:
            name = self._get_field(row, ["name"])
            nfc_tag = self._get_field(row, ["nfc_tag", "nfc_id", "nfc"])
            rfid_tag = self._get_field(row, ["rfid_tag", "rfid_id", "rfid"])
            email = self._get_field(row, ["email"]) or ""

            if not name or not nfc_tag or not rfid_tag:
                raise ValueError("CSV rows must include name, nfc, and rfid")
            if nfc_tag in self.athletes_by_nfc:
                raise ValueError(f"Duplicate NFC tag: {nfc_tag}")
            if rfid_tag in self.athletes_by_rfid:
                raise ValueError(f"Duplicate RFID tag: {rfid_tag}")

            runner = Runner(
                runner_id=runner_id,
                name=name,
                email=email,
                nfc_tag=nfc_tag,
                rfid_tag=rfid_tag,
            )
            session = RunnerSession(runner=runner, restDuration=self.rest_time_seconds)
            self.athletes_by_nfc[nfc_tag] = session #this allows to not auto add athletes to the group when they are loaded from csv, they will be added when they scan their nfc tag
            self.athletes_by_rfid[rfid_tag] = session
            runner_id += 1

        return len(rows)

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

    def handle_rfid_detected(self, rfid_tag: str) -> str:
        self._ensure_active()
        session = self._get_by_rfid(rfid_tag)
        session.record_lap()

        if session.should_finish_interval(self.laps_per_interval):
            session.finish_interval()

        return session.state

    def handle_nfc_scanned(self, nfc_tag: str) -> str:
        self._ensure_active()
        session = self._get_by_nfc(nfc_tag)
        session.start_interval()
        return session.state

    def get_resting_athletes(self) -> List[dict]:
        self._ensure_active()
        resting = []

        for session in self.athletes_by_nfc.values():
            session.check_if_ready()
            if session.state == "RESTING":
                resting.append({
                    "name": session.runner.name,
                    "nfc_tag": session.runner.nfc_tag,
                    "rfid_tag": session.runner.rfid_tag,
                    "state": session.state,
                    "remaining_rest_seconds": session.get_remaining_restDuration(),
                })

        resting.sort(key=lambda x: x["remaining_rest_seconds"])
        return resting

    def get_running_athletes(self) -> List[dict]:
        self._ensure_active()
        running = []

        for session in self.athletes_by_nfc.values():
            if session.state == "RUNNING":
                running.append({
                    "name": session.runner.name,
                    "nfc_tag": session.runner.nfc_tag,
                    "rfid_tag": session.runner.rfid_tag,
                    "state": session.state,
                    "lap_count": self._get_current_lap_count(session),
                })

        return running

    def terminate_workout(self) -> None:
        self.is_terminated = True
        self.current_group.clear()

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

    def _read_csv_rows(self, file_path: str) -> List[dict]:
        with open(file_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    def _get_field(self, row: dict, keys: List[str]) -> Optional[str]:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            value = value.strip()
            if value:
                return value
        return None

    def _get_current_lap_count(self, session: RunnerSession) -> int:
        if not session.intervals:
            return 0
        current_interval = session.intervals[-1]
        return len(current_interval.get("laps", []))
