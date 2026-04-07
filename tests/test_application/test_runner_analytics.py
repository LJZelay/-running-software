import pytest
from datetime import datetime
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.get_runner_analytics import GetRunnerAnalyticsUseCase


def test_runner_analytics_computes_correct_pace():
    # Setup
    repo = InMemoryWorkoutRepository()
    runner = Runner(1, "Alice", "alice@example.com", "NFC001", "RFID001")
    workout = Workout(1, intervalDistance=400, lapsPerInterval=2, startMode="INDIVIDUAL")
    session = RunnerSession(runner, restDuration=60)

    # Simulate intervals
    interval1 = {
        "intervalNumber": 1,
        "start": "2025-01-01T10:00:00",
        "end": "2025-01-01T10:01:00",  # 60 seconds
        "laps": ["2025-01-01T10:00:30", "2025-01-01T10:01:00"]
    }
    interval2 = {
        "intervalNumber": 2,
        "start": "2025-01-01T10:02:00",
        "end": "2025-01-01T10:03:30",  # 90 seconds
        "laps": ["2025-01-01T10:02:45", "2025-01-01T10:03:30"]
    }
    session.intervals = [interval1, interval2]

    workout.add_runner_session(session)
    repo.save(workout)

    # Execute use case
    uc = GetRunnerAnalyticsUseCase(repo)
    results = uc.execute(1)

    assert len(results) == 1
    alice_data = results[0]
    assert alice_data.runner_name == "Alice"
    assert len(alice_data.intervals) == 2

    # Check pace for interval1: 60 sec over 0.4 km = 150 sec/km
    assert alice_data.intervals[0].pace_per_km == pytest.approx(150.0, rel=1e-2)
    # Interval2: 90 sec over 0.4 km = 225 sec/km
    assert alice_data.intervals[1].pace_per_km == pytest.approx(225.0, rel=1e-2)

    # Overall average pace = (150+225)/2 = 187.5
    assert alice_data.overall_avg_pace == pytest.approx(187.5, rel=1e-2)

    # Split times: first interval splits: 30s and 30s (from start to lap1, lap1 to end)
    assert len(alice_data.intervals[0].splits_ms) == 2
    assert alice_data.intervals[0].splits_ms[0] == 30000  # 30 sec in ms
    assert alice_data.intervals[0].splits_ms[1] == 30000