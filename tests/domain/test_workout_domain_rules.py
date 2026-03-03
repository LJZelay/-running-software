"""
Domain unit tests for Workout edge rules.

These tests make sure Workout enforces lifecycle rules and rejects invalid events.
intentionally domain-only (no repository, no use cases) to respect clean architecture
"""

import pytest

from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from domain.states import WORKOUT_NOT_STARTED, WORKOUT_ACTIVE


def _make_workout_with_one_runner() -> Workout:
    """
     Builds a NOT_STARTED workout with one runner session added.
    """
    workout = Workout(
        workout_id=1,
        intervalDistance=400,
        lapsPerInterval=2,
        startMode="INDIVIDUAL",
    )
    runner = Runner(
        runner_id=1,
        name="Test Runner",
        email="",
        nfc_tag="NFC1",
        rfid_tag="RFID1",
    )
    session = RunnerSession(runner=runner, restDuration=10)
    workout.add_runner_session(session)
    return workout


def test_workout_cannot_start_twice():
    """
    Starting a workout twice should not be allowed.
    First start flips NOT_STARTED -> ACTIVE. Second start should return False and keep ACTIVE.
    """
    workout = _make_workout_with_one_runner()

    assert workout.status == WORKOUT_NOT_STARTED

    started_first = workout.start()
    assert started_first is True
    assert workout.status == WORKOUT_ACTIVE

    started_second = workout.start()
    assert started_second is False
    assert workout.status == WORKOUT_ACTIVE


def test_workout_rejects_rfid_if_not_started():
    """
    RFID laps shouldn't be accepted until the coach starts the workout.
    """
    workout = _make_workout_with_one_runner()
    # Workout is still NOT_STARTED here.

    with pytest.raises(ValueError):
        workout.record_rfid_event("RFID1")


def test_cannot_add_runner_after_workout_started():
    """
    Once the workout starts, roster/config should be locked.
    add_runner_session should return False after start.
    """
    workout = Workout(
        workout_id=2,
        intervalDistance=400,
        lapsPerInterval=2,
        startMode="INDIVIDUAL",
    )
    assert workout.start() is True
    assert workout.status == WORKOUT_ACTIVE

    runner = Runner(
        runner_id=2,
        name="Late Runner",
        email="",
        nfc_tag="NFC2",
        rfid_tag="RFID2",
    )
    session = RunnerSession(runner=runner, restDuration=10)

    result = workout.add_runner_session(session)
    assert result is False


def test_workout_rejects_unknown_nfc():
    """
    If someone scans an NFC tag that isn't in the roster,
    the workout should reject it (ValueError).
    """
    workout = _make_workout_with_one_runner()
    assert workout.start() is True

    with pytest.raises(ValueError):
        workout.record_nfc_start("UNKNOWN_TAG")