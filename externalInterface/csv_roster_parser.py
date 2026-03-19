import csv
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


class CSVInputError(Exception):
    pass


@dataclass
class RosterData:
    """Immutable data class for roster entry (not a domain entity)"""
    name: str
    nfc_id: str
    rfid_id: str
    email: Optional[str] = None


class CSVRosterParser:
    """
    Parses a CSV roster and converts it into RosterData objects.
    Format-agnostic from the application perspective.
    """

    REQUIRED_COLUMNS = {"name", "nfc_id", "rfid_id"}  # normalized names

    def __init__(self, strict_validation: bool = True):
        self.strict_validation = strict_validation
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

    # ---------------------------
    # Parsing
    # ---------------------------

    def parse_csv_file(self, file_path: str) -> List[RosterData]:
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                return self._parse_csv_content(f)
        except FileNotFoundError:
            raise CSVInputError(f"File not found: {file_path}")

    def parse_csv_string(self, csv_string: str) -> List[RosterData]:
        return self._parse_csv_content(io.StringIO(csv_string))

    def _parse_csv_content(self, file_obj) -> List[RosterData]:
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

        processed_rows: List[RosterData] = []
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

    def _process_row(self, row: Dict[str, Any], row_num: int) -> RosterData:
        """
        Convert a DictReader row to RosterData object.
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

        return RosterData(
            name=normalized_row["name"],
            nfc_id=normalized_row["nfc_id"],
            rfid_id=normalized_row["rfid_id"],
            email=normalized_row.get("email")
        )

    def validate_unique_tags(self, roster_data: List[RosterData]) -> Tuple[bool, List[str]]:
        """
        Check for duplicate NFC/RFID values.
        """
        errors: List[str] = []
        seen_nfc = set()
        seen_rfid = set()

        for i, data in enumerate(roster_data, start=1):
            nfc = data.nfc_id
            rfid = data.rfid_id

            if nfc in seen_nfc:
                errors.append(f"Row {i}: Duplicate NFC ID '{nfc}'")
            else:
                seen_nfc.add(nfc)

            if rfid in seen_rfid:
                errors.append(f"Row {i}: Duplicate RFID ID '{rfid}'")
            else:
                seen_rfid.add(rfid)

        return (len(errors) == 0, errors)
