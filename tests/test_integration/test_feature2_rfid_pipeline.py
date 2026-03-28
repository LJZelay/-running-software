from datetime import datetime

import pytest

from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.rfid_contracts import RFIDDecision, RFIDReason
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.start_workout import StartWorkoutUseCase
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.runnerState import RunnerState
from domain.workout import Workout


def _build_runner(runner_id: int, name: str, nfc: str, rfid: str) -> Runner:
    return Runner(
        runner_id=runner_id,
        name=name,
        email=f"{name.lower()}@example.com",
        nfc_tag=nfc,
        rfid_tag=rfid,
    )


def _seed_workout_with_runners(workout_id: int, laps_per_interval: int, runners: list[Runner]) -> InMemoryWorkoutRepository:
    workout = Workout(
        workout_id=workout_id,
        intervalDistance=400,
        lapsPerInterval=laps_per_interval,
        startMode="GROUP",
    )
    for runner in runners:
        workout.add_runner_session(RunnerSession(runner=runner, restDuration=30))

    repo = InMemoryWorkoutRepository()
    repo.save(workout)
    return repo


@pytest.mark.integration
def test_nfc_before_workout_activation_is_rejected():
    runner = _build_runner(1, "Alice", "NFC001", "RFID001")
    repo = _seed_workout_with_runners(600, 1, [runner])

    scan_nfc_uc = ScanNFCUseCase(repo)

    with pytest.raises(ValueError, match="Workout is not active"):
        scan_nfc_uc.execute(600, runner.nfc_tag, "2026-02-08T10:00:00", use_event_time=True)


@pytest.mark.integration
def test_rfid_finish_matches_correct_runner_and_starts_rest():
    alice = _build_runner(1, "Alice", "NFC001", "RFID001")
    bob = _build_runner(2, "Bob", "NFC002", "RFID002")
    repo = _seed_workout_with_runners(601, 1, [alice, bob])

    StartWorkoutUseCase(repo).execute(601)
    scan_nfc_uc = ScanNFCUseCase(repo)
    scan_nfc_uc.execute(601, alice.nfc_tag, "2026-02-08T10:00:00", use_event_time=True)
    scan_nfc_uc.execute(601, bob.nfc_tag, "2026-02-08T10:00:01", use_event_time=True)

    result = ScanRFIDUseCase(repo).execute(601, alice.rfid_tag, "2026-02-08T10:00:05", use_event_time=True)

    assert result.decision == RFIDDecision.ACCEPTED
    assert result.reason == RFIDReason.VALID_FINISH

    saved = repo.get_by_id(601)
    assert saved is not None

    by_rfid = {rs.runner.rfid_tag: rs for rs in saved.runnerSessions}
    assert by_rfid[alice.rfid_tag].state == RunnerState.RESTING
    assert by_rfid[bob.rfid_tag].state == RunnerState.RUNNING


@pytest.mark.integration
def test_duplicate_rfid_within_window_is_ignored_without_extra_finish_event():
    runner = _build_runner(1, "Alice", "NFC001", "RFID001")
    repo = _seed_workout_with_runners(602, 4, [runner])

    StartWorkoutUseCase(repo).execute(602)
    ScanNFCUseCase(repo).execute(602, runner.nfc_tag, "2026-02-08T10:00:00", use_event_time=True)

    scan_rfid_uc = ScanRFIDUseCase(repo)
    accepted = scan_rfid_uc.execute(602, runner.rfid_tag, "2026-02-08T10:00:05", use_event_time=True)
    duplicate = scan_rfid_uc.execute(602, runner.rfid_tag, "2026-02-08T10:00:05.050000", use_event_time=True)

    assert accepted.decision == RFIDDecision.ACCEPTED
    assert duplicate.decision == RFIDDecision.IGNORED
    assert duplicate.reason == RFIDReason.DUPLICATE_WITHIN_WINDOW

    saved = repo.get_by_id(602)
    assert saved is not None
    rs = saved.runnerSessions[0]
    assert len(rs.intervals) == 1
    assert len(rs.intervals[0]["laps"]) == 1
    assert rs.state == RunnerState.RUNNING
    assert len(rs.rests) == 0


@pytest.mark.integration
def test_rest_screen_updates_after_rfid_finish():
    runner = _build_runner(1, "Alice", "NFC001", "RFID001")
    repo = _seed_workout_with_runners(603, 1, [runner])

    base_time = datetime.now().replace(microsecond=0)

    StartWorkoutUseCase(repo).execute(603)
    ScanNFCUseCase(repo).execute(603, runner.nfc_tag, base_time.isoformat(), use_event_time=True)
    ScanRFIDUseCase(repo).execute(603, runner.rfid_tag, base_time.isoformat(), use_event_time=True)

    rest_rows = GetRestScreenUseCase(repo).execute(603)

    assert len(rest_rows) == 1
    assert rest_rows[0].runner_name == "Alice"
    assert rest_rows[0].remaining_rest_seconds >= 0


@pytest.mark.integration
def test_scan_rfid_uses_host_clock_when_event_time_disabled(monkeypatch):
    runner = _build_runner(1, "Alice", "NFC001", "RFID001")
    repo = _seed_workout_with_runners(604, 1, [runner])

    StartWorkoutUseCase(repo).execute(604)
    ScanNFCUseCase(repo).execute(604, runner.nfc_tag, "2026-02-08T10:00:00", use_event_time=True)

    fixed_now = datetime(2026, 2, 8, 10, 0, 30)

    class _FixedDateTime:
        @staticmethod
        def now():
            return fixed_now

        @staticmethod
        def fromisoformat(value: str):
            return datetime.fromisoformat(value)

    import domain.runnerSession as runner_session_module

    monkeypatch.setattr(runner_session_module, "datetime", _FixedDateTime)

    result = ScanRFIDUseCase(repo).execute(
        604,
        runner.rfid_tag,
        "1900-01-01T00:00:00",
        use_event_time=False,
    )

    assert result.decision == RFIDDecision.ACCEPTED

    saved = repo.get_by_id(604)
    assert saved is not None
    interval_end = saved.runnerSessions[0].intervals[0]["end"]
    assert interval_end == fixed_now.isoformat()