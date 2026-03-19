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

    workout.record_nfc_start("NFC1")

    workout.record_rfid_event("RFID1")
    workout.record_rfid_event("RFID1")

    assert session.state == RunnerState.RESTING

def test_unknown_rfid_raises_error():
    workout, _ = create_workout_with_runner()

    with pytest.raises(ValueError):
        workout.record_rfid_event("UNKNOWN")