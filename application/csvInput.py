import csv
import io
from typing import List, Dict, Any, Optional, Tuple

from domain.runner import Runner
from domain.runnerSession import RunnerSession


class CSVInputError(Exception):
    pass


class CSVInputParser:
    """
    Parses a CSV roster and converts it into domain objects.
    """

    REQUIRED_COLUMNS = {"name", "nfc_id", "rfid_id"}  # normalized names

    def __init__(self, strict_validation: bool = True):
        self.strict_validation = strict_validation
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

    # ---------------------------
    # Parsing
    # ---------------------------

    def parse_csv_file(self, file_path: str) -> List[Dict[str, str]]:
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                return self._parse_csv_content(f)
        except FileNotFoundError:
            raise CSVInputError(f"File not found: {file_path}")

    def parse_csv_string(self, csv_string: str) -> List[Dict[str, str]]:
        return self._parse_csv_content(io.StringIO(csv_string))

    def _parse_csv_content(self, file_obj) -> List[Dict[str, str]]:
        self.validation_errors.clear()
        self.warnings.clear()

        reader = csv.DictReader(file_obj)
        if not reader.fieldnames:
            raise CSVInputError("CSV file has no headers")

        rows = list(reader)
        if not rows:
            raise CSVInputError("CSV file is empty")

        # validate headers (normalized)
        normalized_headers = self._normalize_headers(reader.fieldnames)
        self._validate_headers(normalized_headers)

        if self.validation_errors and self.strict_validation:
            raise CSVInputError(self.validation_errors[0])

        processed_rows: List[Dict[str, str]] = []
        for i, row in enumerate(rows, start=1):
            try:
                processed_rows.append(self._process_row(row, i))
            except CSVInputError as e:
                if self.strict_validation:
                    raise
                self.validation_errors.append(str(e))

        return processed_rows

    def _normalize_headers(self, headers: List[str]) -> Dict[str, str]:
        """
        Maps original header -> normalized header.
        We keep this simple and accept common variants.
        """
        mapping: Dict[str, str] = {}
        for h in headers:
            key = (h or "").strip().lower()

            if key in ("name",):
                mapping[h] = "name"
            elif key in ("nfc_id", "nfc", "nfc tag", "nfc tag id", "nfc tag_id"):
                mapping[h] = "nfc_id"
            elif key in ("rfid_id", "rfid", "rfid tag", "rfid tag id", "rfid tag_id"):
                mapping[h] = "rfid_id"
            elif key in ("email", "e-mail"):
                mapping[h] = "email"
            else:
                mapping[h] = key  # keep unknown columns (won't be required)
        return mapping

    def _validate_headers(self, normalized_headers: Dict[str, str]) -> None:
        present = set(normalized_headers.values())

        for required in self.REQUIRED_COLUMNS:
            if required not in present:
                self.validation_errors.append(f"Missing required column: {required}")

    def _process_row(self, row: Dict[str, Any], row_num: int) -> Dict[str, str]:
        """
        Convert a DictReader row to normalized field dict:
          name, nfc_id, rfid_id, email(optional)
        """
        # Normalize keys/values
        normalized_row: Dict[str, str] = {}

        for original_key, value in row.items():
            if original_key is None:
                continue
            norm_key = original_key.strip().lower()
            val = value.strip() if isinstance(value, str) else ""

            # apply same alias logic as headers
            if norm_key == "name":
                normalized_row["name"] = val
            elif norm_key in ("nfc_id", "nfc", "nfc tag", "nfc tag id", "nfc tag_id"):
                normalized_row["nfc_id"] = val
            elif norm_key in ("rfid_id", "rfid", "rfid tag", "rfid tag id", "rfid tag_id"):
                normalized_row["rfid_id"] = val
            elif norm_key in ("email", "e-mail"):
                normalized_row["email"] = val

        # validate required
        for req in self.REQUIRED_COLUMNS:
            if req not in normalized_row or not normalized_row[req]:
                raise CSVInputError(f"Row {row_num}: Missing required field '{req}'")

        # simple validation
        if len(normalized_row["name"]) < 2:
            raise CSVInputError(f"Row {row_num}: Name is too short")

        if "email" in normalized_row and normalized_row["email"]:
            if "@" not in normalized_row["email"]:
                raise CSVInputError(f"Row {row_num}: Invalid email '{normalized_row['email']}'")

        return normalized_row

    # ---------------------------
    # Domain object creation
    # ---------------------------

    def create_runners(self, csv_rows: List[Dict[str, str]], starting_id: int = 1) -> List[Runner]:
        """
        Create Runner objects from parsed CSV rows.
        Runner IDs are generated incrementally.
        """
        runners: List[Runner] = []
        for i, row in enumerate(csv_rows):
            runners.append(
                Runner(
                    runner_id=starting_id + i,
                    name=row["name"],
                    email=row.get("email", ""),  # optional
                    nfc_tag=row["nfc_id"],
                    rfid_tag=row["rfid_id"],
                )
            )
        return runners

    def create_runner_sessions(
        self,
        runners: List[Runner],
        default_rest_duration: int,
    ) -> List[RunnerSession]:
        """
        Create RunnerSession objects with a default rest duration.
        You can override per runner later if you want.
        """
        return [RunnerSession(runner=r, restDuration=default_rest_duration) for r in runners]

    def validate_unique_tags(self, csv_rows: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
        """
        Optional helper: check for duplicate NFC/RFID values.
        """
        errors: List[str] = []
        seen_nfc = set()
        seen_rfid = set()

        for i, row in enumerate(csv_rows, start=1):
            nfc = row["nfc_id"]
            rfid = row["rfid_id"]

            if nfc in seen_nfc:
                errors.append(f"Row {i}: Duplicate NFC ID '{nfc}'")
            else:
                seen_nfc.add(nfc)

            if rfid in seen_rfid:
                errors.append(f"Row {i}: Duplicate RFID ID '{rfid}'")
            else:
                seen_rfid.add(rfid)

        return (len(errors) == 0, errors)
