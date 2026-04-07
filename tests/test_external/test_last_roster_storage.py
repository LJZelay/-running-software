"""
Tests for last roster save/load behavior.

Plain-speak:
These tests make sure the app can save the most recent roster,
load it back later, and handle bad or missing files cleanly.
"""

from pathlib import Path
import pytest

from domain.runner import Runner
from externalInterface.last_roster_storage import (
    save_last_roster,
    load_last_roster,
    last_roster_exists,
)


def _make_runner(runner_id: int, name: str, email: str, nfc_tag: str, rfid_tag: str) -> Runner:
    """
    Plain-speak:
    Small helper so we don't repeat Runner setup in every test.
    """
    return Runner(
        runner_id=runner_id,
        name=name,
        email=email,
        nfc_tag=nfc_tag,
        rfid_tag=rfid_tag,
    )


def test_last_roster_exists_returns_false_when_file_missing(tmp_path: Path):
    """
    Plain-speak:
    If no saved roster file exists yet, the helper should report False.
    """
    file_path = tmp_path / "last_roster.csv"

    assert last_roster_exists(file_path) is False


def test_save_and_load_last_roster_preserves_runner_fields(tmp_path: Path):
    """
    Plain-speak:
    Saving and loading should preserve the important roster data:
    name, email, NFC tag, and RFID tag.
    """
    file_path = tmp_path / "last_roster.csv"

    original_runners = [
        _make_runner(1, "Alice", "alice@example.com", "NFC001", "RFID001"),
        _make_runner(2, "Bob", "bob@example.com", "NFC002", "RFID002"),
    ]

    save_last_roster(original_runners, file_path)

    assert last_roster_exists(file_path) is True

    loaded_runners = load_last_roster(file_path)

    assert len(loaded_runners) == 2

    assert loaded_runners[0].name == "Alice"
    assert loaded_runners[0].email == "alice@example.com"
    assert loaded_runners[0].nfc_tag == "NFC001"
    assert loaded_runners[0].rfid_tag == "RFID001"

    assert loaded_runners[1].name == "Bob"
    assert loaded_runners[1].email == "bob@example.com"
    assert loaded_runners[1].nfc_tag == "NFC002"
    assert loaded_runners[1].rfid_tag == "RFID002"


def test_load_last_roster_raises_error_for_malformed_csv(tmp_path: Path):
    """
    Plain-speak:
    If the saved CSV is missing required columns, loading it should fail
    instead of silently creating broken runners.
    """
    file_path = tmp_path / "last_roster.csv"

    # Missing the rfid_tag column on purpose.
    file_path.write_text(
        "name,email,nfc_tag\n"
        "Alice,alice@example.com,NFC001\n",
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        load_last_roster(file_path)


def test_save_last_roster_overwrites_previous_saved_roster(tmp_path: Path):
    """
    Plain-speak:
    This feature is supposed to remember the LAST known roster.
    Saving a new roster should replace the old one.
    """
    file_path = tmp_path / "last_roster.csv"

    old_roster = [
        _make_runner(1, "Alice", "alice@example.com", "NFC001", "RFID001"),
    ]

    new_roster = [
        _make_runner(1, "Charlie", "charlie@example.com", "NFC003", "RFID003"),
        _make_runner(2, "Diana", "diana@example.com", "NFC004", "RFID004"),
    ]

    save_last_roster(old_roster, file_path)
    save_last_roster(new_roster, file_path)

    loaded_runners = load_last_roster(file_path)

    assert len(loaded_runners) == 2
    assert loaded_runners[0].name == "Charlie"
    assert loaded_runners[1].name == "Diana"

def test_save_and_load_empty_roster(tmp_path):
    """Plain-speak:
    Saving an emprty roster shoudl still make a valid file.
    Loading that file back should return an empty list, not crash.
    """

    file_path = tmp_path / "last_roster.csv"
    save_last_roster([], file_path)
    assert last_roster_exists(file_path) is True
    loaded_runners = load_last_roster(file_path)
    assert loaded_runners == []

def test_load_last_roster_preserves_runner_order(tmp_path:Path):
    file_path = tmp_path / "last_roster.csv"

    original_runners = [
        _make_runner(1, "Alice", "alice@example.com", "NFC001", "RFID001"),
        _make_runner(2, "Bob", "bob@example.com", "NFC002", "RFID002"),
        _make_runner(3, "Charlie", "charlie@example.com", "NFC003", "RFID003"),
    ]

    save_last_roster(original_runners, file_path)
    loaded_runners = load_last_roster(file_path)

    assert [runner.name for runner in loaded_runners] == ["Alice", "Bob", "Charlie"]

def test_save_last_roster_creates_missing_parent_directory(tmp_path: Path):
    file_path = tmp_path / "nested" / "folder" / "last_roster.csv"

    runners = [_make_runner(1, "Alice", "alice@example.com", "NFC001", "RFID001")]

    save_last_roster(runners, file_path)
    assert file_path.exists() is True
    loaded_runners = load_last_roster(file_path)
    assert len(loaded_runners) == 1
    assert loaded_runners[0].name == "Alice"