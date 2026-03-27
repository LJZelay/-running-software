import pytest
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from domain.workoutState import WorkoutState
from domain.runnerState import RunnerState

def create_workout_with_runner():
    runner = Runner(
        runner_id=1,
        name="Clifford Wijaya",
        email="cwijaya@example.com",
        nfc_tag="NFC1",
        rfid_tag="RFID1"
    )
    session = RunnerSession(runner=runner, restDuration=10)
    workout = Workout(
        workout_id=1,
        intervalDistance=400,
        lapsPerInterval=2,
        startMode="INDIVIDUAL"
    )

    workout.add_runner_session(session)
    workout.start()

    return workout, session

def test_workout_start():
    workout = Workout(
        workout_id=1,
        intervalDistance=400,
        lapsPerInterval=2,
        startMode="INDIVIDUAL"
    )

    assert workout.status == WorkoutState.NOT_STARTED

    started = workout.start()

    assert started is True
    assert workout.status == WorkoutState.ACTIVE

def test_rfid_completes_interval():
    workout, session = create_workout_with_runner()

    workout.record_nfc_start("NFC1", "2026-02-08T10:00:00")

    workout.record_rfid_event("RFID1", "2026-02-08T10:00:01")
    workout.record_rfid_event("RFID1", "2026-02-08T10:00:02")

    assert session.state == RunnerState.RESTING

def test_unknown_rfid_is_ignored_without_mutation():
    workout, _ = create_workout_with_runner()

    result = workout.record_rfid_event("UNKNOWN")

    assert result.decision == "ignored"
    assert result.reason == "unknown_tag"