import pytest
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.get_workout_stats import GetWorkoutStatsUseCase


def test_workout_stats_aggregates_correctly():
    repo = InMemoryWorkoutRepository()
    workout = Workout(1, intervalDistance=400, lapsPerInterval=1, startMode="INDIVIDUAL")

    # Runner1 completes 2 intervals
    runner1 = Runner(1, "Alice", "a@a.com", "NFC1", "RFID1")
    s1 = RunnerSession(runner1, restDuration=60)
    s1.intervals = [
        {"intervalNumber": 1, "start": "2025-01-01T10:00:00", "end": "2025-01-01T10:01:00", "laps": []},
        {"intervalNumber": 2, "start": "2025-01-01T10:02:00", "end": "2025-01-01T10:03:00", "laps": []}
    ]
    # Runner2 completes 1 interval
    runner2 = Runner(2, "Bob", "b@b.com", "NFC2", "RFID2")
    s2 = RunnerSession(runner2, restDuration=60)
    s2.intervals = [
        {"intervalNumber": 1, "start": "2025-01-01T10:00:00", "end": "2025-01-01T10:01:00", "laps": []}
    ]
    workout.add_runner_session(s1)
    workout.add_runner_session(s2)
    repo.save(workout)

    uc = GetWorkoutStatsUseCase(repo)
    stats = uc.execute(1)

    assert stats.total_runners == 2
    assert stats.intervals_completed[1] == 2
    assert stats.intervals_completed[2] == 1
    # We haven't added actual pace calculations in this test, but we could.