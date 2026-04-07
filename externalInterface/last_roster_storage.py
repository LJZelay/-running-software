import csv
from pathlib import Path
from typing import List
from domain.runner import Runner

DEFAULT_LAST_ROSTER_PATH = Path("data/last_roster.csv")


def save_last_roster(runners: List[Runner], file_path: Path = DEFAULT_LAST_ROSTER_PATH) -> None:
    print(f"DEBUG: saving to {file_path.resolve()}")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "email", "nfc_tag", "rfid_tag"])

        for runner in runners:
            writer.writerow([
                runner.name,
                runner.email,
                runner.nfc_tag,
                runner.rfid_tag,
            ])


def load_last_roster(file_path: Path = DEFAULT_LAST_ROSTER_PATH) -> List[Runner]:
    runners = []

    with open(file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, start=1):
            runners.append(
                Runner(
                    runner_id=idx,
                    name=row["name"],
                    email=row["email"],
                    nfc_tag=row["nfc_tag"],
                    rfid_tag=row["rfid_tag"],
                )
            )

    return runners


def last_roster_exists(file_path: Path = DEFAULT_LAST_ROSTER_PATH) -> bool:
    return file_path.exists()