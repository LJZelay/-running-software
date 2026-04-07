import csv
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from externalInterface.csv_roster_parser import CSVInputError


@dataclass
class WorkoutConfig:
    workout_id: Optional[int]
    interval_distance: int
    laps_per_interval: int
    start_mode: str


class CSVWorkoutConfigParser:
    """Parses a CSV workout configuration row into a WorkoutConfig."""

    REQUIRED_COLUMNS = {"intervalDistance", "lapsPerInterval"}
    VALID_START_MODES = {"INDIVIDUAL", "GROUP"}

    def __init__(self):
        self.validation_errors: List[str] = []

    def parse_csv_file(self, file_path: str) -> WorkoutConfig:
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                return self._parse_csv_content(f)
        except FileNotFoundError:
            raise CSVInputError(f"File not found: {file_path}")

    def parse_csv_string(self, csv_string: str) -> WorkoutConfig:
        from io import StringIO
        return self._parse_csv_content(StringIO(csv_string))

    def _parse_csv_content(self, file_obj: Any) -> WorkoutConfig:
        self.validation_errors.clear()

        reader = csv.DictReader(file_obj)
        if not reader.fieldnames:
            raise CSVInputError("CSV file has no headers")

        rows = list(reader)
        if not rows:
            raise CSVInputError("CSV file is empty")

        normalized_headers = self._normalize_headers(reader.fieldnames)
        self._validate_headers(normalized_headers)
        if self.validation_errors:
            raise CSVInputError(self.validation_errors[0])

        return self._process_row(rows[0], 1)

    def _normalize_headers(self, headers: List[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for h in headers:
            key = (h or "").strip().lower()
            if key in ("intervaldistance", "interval_distance", "interval distance", "distance"):
                mapping[h] = "intervalDistance"
            elif key in ("lapsperinterval", "laps_per_interval", "laps per interval", "laps"):
                mapping[h] = "lapsPerInterval"
            elif key in ("startmode", "start_mode", "start mode"):
                mapping[h] = "startMode"
            elif key in ("workoutid", "workout_id", "workout id", "id"):
                mapping[h] = "workout_id"
            else:
                mapping[h] = key
        return mapping

    def _validate_headers(self, normalized_headers: Dict[str, str]) -> None:
        present = set(normalized_headers.values())
        for required in self.REQUIRED_COLUMNS:
            if required not in present:
                self.validation_errors.append(f"Missing required column: {required}")

    def _process_row(self, row: Dict[str, Any], row_num: int) -> WorkoutConfig:
        normalized_row: Dict[str, str] = {}
        for original_key, value in row.items():
            if original_key is None:
                continue
            key = original_key.strip().lower()
            val = value.strip() if isinstance(value, str) else ""
            if key in ("intervaldistance", "interval_distance", "interval distance", "distance"):
                normalized_row["intervalDistance"] = val
            elif key in ("lapsperinterval", "laps_per_interval", "laps per interval", "laps"):
                normalized_row["lapsPerInterval"] = val
            elif key in ("startmode", "start_mode", "start mode"):
                normalized_row["startMode"] = val
            elif key in ("workoutid", "workout_id", "workout id", "id"):
                normalized_row["workout_id"] = val

        for req in self.REQUIRED_COLUMNS:
            if req not in normalized_row or not normalized_row[req]:
                raise CSVInputError(f"Row {row_num}: Missing required field '{req}'")

        try:
            interval_distance = int(normalized_row["intervalDistance"])
        except ValueError:
            raise CSVInputError(f"Row {row_num}: intervalDistance must be an integer")
        if interval_distance <= 0:
            raise CSVInputError(f"Row {row_num}: intervalDistance must be positive")

        try:
            laps_per_interval = int(normalized_row["lapsPerInterval"])
        except ValueError:
            raise CSVInputError(f"Row {row_num}: lapsPerInterval must be an integer")
        if laps_per_interval <= 0:
            raise CSVInputError(f"Row {row_num}: lapsPerInterval must be positive")

        workout_id = None
        if "workout_id" in normalized_row and normalized_row["workout_id"]:
            try:
                workout_id = int(normalized_row["workout_id"])
            except ValueError:
                raise CSVInputError(f"Row {row_num}: workout_id must be an integer")
            if workout_id <= 0:
                raise CSVInputError(f"Row {row_num}: workout_id must be positive")

        start_mode = normalized_row.get("startMode", "INDIVIDUAL").strip().upper() or "INDIVIDUAL"
        if start_mode not in self.VALID_START_MODES:
            raise CSVInputError(f"Row {row_num}: startMode must be INDIVIDUAL or GROUP")

        return WorkoutConfig(
            workout_id=workout_id,
            interval_distance=interval_distance,
            laps_per_interval=laps_per_interval,
            start_mode=start_mode
        )
