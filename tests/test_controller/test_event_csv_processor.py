import csv
from types import SimpleNamespace

from controller.cli import EventCSVProcessor


class _DummyCLI:
    pass


def test_parse_events_allows_start_row_without_tag(tmp_path):
    csv_path = tmp_path / "events.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["TYPE", "TIMESTAMP", "TAG"])
        writer.writerow(["GROUP", "1704067200000", "NFC001"])
        writer.writerow(["START", "1704067200000"])  # Missing TAG column value on purpose
        writer.writerow(["NFC", "1704067205000", "NFC001"])

    processor = EventCSVProcessor(_DummyCLI())
    events = processor._parse_events_file(str(csv_path))

    assert len(events) == 3
    assert events[1]["type"] == "START"
    assert events[1]["tag"] == ""


class _StubGroupStartUseCase:
    def __init__(self):
        self.calls = []

    def execute(self, workout_id, group_nfc_tags=None):
        self.calls.append((workout_id, list(group_nfc_tags or [])))
        return (6, 6, 0)


class _ReplayCLIStub:
    def __init__(self):
        self.workout_id = 1
        self.group_nfc_tags = []
        self.group_start_uc = _StubGroupStartUseCase()
        self.scan_nfc_uc = None
        self.scan_rfid_uc = None

    def _find_runner_by_nfc(self, nfc_tag):
        return SimpleNamespace(runner=SimpleNamespace(name=f"Runner-{nfc_tag}"))

    def _find_runner_by_rfid(self, _rfid_tag):
        return None


def test_process_events_executes_start_when_group_populated(tmp_path):
    csv_path = tmp_path / "events.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["TYPE", "TIMESTAMP", "TAG"])
        writer.writerow(["GROUP", "1704067200000", "NFC001"])
        writer.writerow(["START", "1704067201000", ""])

    cli = _ReplayCLIStub()
    processor = EventCSVProcessor(cli)

    success, errors = processor.process_file(str(csv_path))

    assert success is True
    assert errors == []
    assert cli.group_start_uc.calls == [(1, ["NFC001"])]
    assert cli.group_nfc_tags == []
