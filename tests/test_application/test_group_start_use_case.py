import pytest

from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.group_start import GroupStartUseCase
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.runnerState import RunnerState
from domain.workout import Workout


@pytest.mark.application
def test_group_start_prepares_not_started_runner_sessions():
    repo = InMemoryWorkoutRepository()
    workout = Workout(
        workout_id=1,
        intervalDistance=400,
        lapsPerInterval=1,
        startMode="GROUP",
    )

    workout.add_runner_session(
        RunnerSession(
            runner=Runner(1, "Alice", "alice@example.com", "NFC001", "RFID001"),
            restDuration=60,
            state=RunnerState.NOT_STARTED,
        )
    )
    workout.add_runner_session(
        RunnerSession(
            runner=Runner(2, "Bob", "bob@example.com", "NFC002", "RFID002"),
            restDuration=60,
            state=RunnerState.NOT_STARTED,
        )
    )

    repo.save(workout)

    ready_count, active_count, resting_count = GroupStartUseCase(repo).execute(1)

    assert ready_count == 2
    assert active_count == 2
    assert resting_count == 0

    saved = repo.get_by_id(1)
    assert saved is not None
    assert saved.is_active() is True
    assert all(rs.state == RunnerState.RUNNING for rs in saved.runnerSessions)

    start_timestamps = [rs.intervals[0]["start"] for rs in saved.runnerSessions]
    assert len(set(start_timestamps)) == 1
    assert all(ts is not None for ts in start_timestamps)


@pytest.mark.application
def test_group_start_prepares_only_selected_group_runners():
    repo = InMemoryWorkoutRepository()
    workout = Workout(
        workout_id=2,
        intervalDistance=400,
        lapsPerInterval=1,
        startMode="GROUP",
    )

    workout.add_runner_session(
        RunnerSession(
            runner=Runner(1, "Alice", "alice@example.com", "NFC001", "RFID001"),
            restDuration=60,
            state=RunnerState.NOT_STARTED,
        )
    )
    workout.add_runner_session(
        RunnerSession(
            runner=Runner(2, "Bob", "bob@example.com", "NFC002", "RFID002"),
            restDuration=60,
            state=RunnerState.NOT_STARTED,
        )
    )

    repo.save(workout)

    ready_count, active_count, resting_count = GroupStartUseCase(repo).execute(2, ["NFC001"])

    assert ready_count == 1
    assert active_count == 1
    assert resting_count == 0

    saved = repo.get_by_id(2)
    assert saved is not None
    states_by_nfc = {rs.runner.nfc_tag: rs.state for rs in saved.runnerSessions}
    assert states_by_nfc["NFC001"] == RunnerState.RUNNING
    assert states_by_nfc["NFC002"] == RunnerState.NOT_STARTED
    assert saved.runnerSessions[0].intervals[0]["start"] is not None
