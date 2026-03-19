import csv
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ParsedAthlete:
    first_name: str
    last_name: str
    rfid_tag: str
    nfc_tag: str
    email: str = ""


@dataclass(frozen=True)
class ParsedCommand:
    command_type: str
    timestamp_ms: Optional[int] = None
    nfc_tags: Optional[List[str]] = None
    nfc_tag: Optional[str] = None
    rfid_tag: Optional[str] = None


class SimulationCSVError(ValueError):
    pass


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def _parse_int(value: str, field_name: str) -> int:
    text = (value or "").strip()
    if not text:
        raise SimulationCSVError(f"Missing {field_name}")
    try:
        return int(text)
    except ValueError as exc:
        raise SimulationCSVError(f"Invalid {field_name}: {text}") from exc


def parse_athletes_csv(file_path: str) -> List[ParsedAthlete]:
    with open(file_path, "r", newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)

        if not reader.fieldnames:
            raise SimulationCSVError("athletes.csv must contain a header row")

        normalized_headers: Dict[str, str] = {_norm(header): header for header in reader.fieldnames}

        def read_field(row: Dict[str, str], *aliases: str) -> str:
            for alias in aliases:
                original_name = normalized_headers.get(_norm(alias))
                if original_name is not None:
                    return (row.get(original_name) or "").strip()
            return ""

        athletes: List[ParsedAthlete] = []

        for row_index, row in enumerate(reader, start=2):
            first_name = read_field(row, "First Name")
            last_name = read_field(row, "Last Name")

            if not first_name and not last_name:
                full_name = read_field(row, "name")
                if full_name:
                    name_parts = [part for part in full_name.split(" ") if part]
                    first_name = name_parts[0] if name_parts else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            nfc_tag = read_field(row, "NFC TAG", "nfc_id", "nfc")
            rfid_tag = read_field(row, "RFID TAG", "rfid_id", "rfid")
            email = read_field(row, "email")

            if not first_name or not nfc_tag or not rfid_tag:
                raise SimulationCSVError(
                    "Invalid athlete row at line "
                    f"{row_index}: expected at least first name, NFC tag, and RFID tag"
                )

            athletes.append(
                ParsedAthlete(
                    first_name=first_name,
                    last_name=last_name,
                    rfid_tag=rfid_tag,
                    nfc_tag=nfc_tag,
                    email=email,
                )
            )

        if not athletes:
            raise SimulationCSVError("athletes.csv has no athlete rows")

        return athletes


def parse_commands_csv(file_path: str) -> List[ParsedCommand]:
    commands: List[ParsedCommand] = []

    with open(file_path, "r", newline="", encoding="utf-8") as file_obj:
        reader = csv.reader(file_obj)

        for row in reader:
            if not row:
                continue

            first_cell = (row[0] or "").strip()
            if not first_cell:
                continue

            command_type = first_cell.upper()

            # Skip known header row
            if command_type == "TYPE":
                continue

            if command_type == "GROUP":
                # Assignment format: GROUP, NFC1, NFC2, ...
                # Existing project format: GROUP, TIMESTAMP, NFC1
                if len(row) >= 3 and (row[1] or "").strip().isdigit():
                    possible_tag = (row[2] or "").strip()
                    tags = [possible_tag] if possible_tag else []
                else:
                    tags = [(cell or "").strip() for cell in row[1:] if (cell or "").strip()]

                commands.append(ParsedCommand(command_type="GROUP", nfc_tags=tags))
                continue

            if command_type == "START":
                if len(row) < 2:
                    raise SimulationCSVError("START command is missing timestamp")
                commands.append(
                    ParsedCommand(
                        command_type="START",
                        timestamp_ms=_parse_int(row[1], "START timestamp"),
                    )
                )
                continue

            if command_type in {"NFC", "RFID"}:
                if len(row) < 3:
                    raise SimulationCSVError(f"{command_type} command is missing fields")

                # Assignment format: NFC, NFC_tag, TIMESTAMP
                if (row[2] or "").strip().isdigit():
                    tag_value = (row[1] or "").strip()
                    timestamp_ms = _parse_int(row[2], f"{command_type} timestamp")
                else:
                    # Existing project format: NFC, TIMESTAMP, NFC_tag
                    timestamp_ms = _parse_int(row[1], f"{command_type} timestamp")
                    tag_value = (row[2] or "").strip()

                if command_type == "NFC":
                    commands.append(
                        ParsedCommand(command_type="NFC", nfc_tag=tag_value, timestamp_ms=timestamp_ms)
                    )
                else:
                    commands.append(
                        ParsedCommand(command_type="RFID", rfid_tag=tag_value, timestamp_ms=timestamp_ms)
                    )
                continue

            raise SimulationCSVError(f"Unknown command type: {first_cell}")

    return commands
