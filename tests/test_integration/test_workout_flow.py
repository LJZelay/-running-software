"""Integration tests for complete workout flow."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import csv
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from domain.workoutState import WorkoutState
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.start_workout import StartWorkoutUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.end_workout import EndWorkoutUseCase


# Path to actual test data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
ATHLETES_CSV = DATA_DIR / "athletes.csv"


def load_athletes_from_csv(limit: int = None) -> list[Runner]:
    """Load athletes from CSV file."""
    athletes = []
    with open(ATHLETES_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if limit and idx > limit:
                break
            athlete = Runner(
                runner_id=idx,
                name=row['name'],
                email=row['email'],
                nfc_tag=row['nfc_id'],
                rfid_tag=row['rfid_id']
            )
            athletes.append(athlete)
    return athletes


@pytest.mark.integration
class TestIntervalWorkoutFlow:
    """Test complete interval workout lifecycle."""

    def test_complete_workout_with_single_runner(self):
        """Test a complete workout start, run, and end with one runner."""
        # Load athlete data from CSV
        athletes = load_athletes_from_csv(limit=1)
        runner = athletes[0]
        
        workout = Workout(
            workout_id=100,
            intervalDistance=400,
            lapsPerInterval=4,
            startMode="INDIVIDUAL"
        )
        
        runner_session = RunnerSession(runner=runner, restDuration=30)
        workout.add_runner_session(runner_session)
        
        # Initialize repository and save workout
        repository = InMemoryWorkoutRepository()
        repository.save(workout)
        
        # Start workout
        start_use_case = StartWorkoutUseCase(repository)
        started = start_use_case.execute(100)
        assert started is True
        
        # Scan NFC to start running
        scan_nfc_use_case = ScanNFCUseCase(repository)
        status = scan_nfc_use_case.execute(100, runner.nfc_tag, "2026-02-08T10:00:00")
        
        assert status.workout_id == 100
        assert status.workout_state == WorkoutState.ACTIVE.value
        assert status.active_runner_count == 1
        
        # Record laps via RFID
        scan_rfid_use_case = ScanRFIDUseCase(repository)
        
        # Simulate 4 lap completions
        for i in range(4):
            status = scan_rfid_use_case.execute(
                100,
                runner.rfid_tag,
                f"2026-02-08T10:00:{5+i*5:02d}",
                use_event_time=True,
            )
        
        # After 4th lap, runner should be resting
        assert status.active_runner_count == 0
        assert status.resting_runner_count == 1
        
        # End workout
        end_use_case = EndWorkoutUseCase(repository)
        ended = end_use_case.execute(100)
        assert ended is True
        
        # Verify final state
        final_workout = repository.get_by_id(100)
        assert final_workout.status == WorkoutState.COMPLETED

    def test_complete_workout_with_multiple_runners(self):
        """Test a complete workout with two runners."""
        # Load athlete data from CSV
        athletes = load_athletes_from_csv(limit=2)
        runner1 = athletes[0]
        runner2 = athletes[1]
        
        workout = Workout(
            workout_id=200,
            intervalDistance=400,
            lapsPerInterval=4,
            startMode="INDIVIDUAL"
        )
        
        workout.add_runner_session(RunnerSession(runner=runner1, restDuration=30))
        workout.add_runner_session(RunnerSession(runner=runner2, restDuration=30))
        
        # Initialize and save
        repository = InMemoryWorkoutRepository()
        repository.save(workout)
        
        # Start workout
        start_use_case = StartWorkoutUseCase(repository)
        assert start_use_case.execute(200) is True
        
        # Both runners scan NFC
        scan_nfc_use_case = ScanNFCUseCase(repository)
        status1 = scan_nfc_use_case.execute(200, runner1.nfc_tag, "2026-02-08T10:00:00")
        status2 = scan_nfc_use_case.execute(200, runner2.nfc_tag, "2026-02-08T10:00:02")
        
        # After first runner: 1 active
        assert status1.active_runner_count == 1
        # After second runner: 2 active
        assert status2.active_runner_count == 2
        
        # End workout
        end_use_case = EndWorkoutUseCase(repository)
        assert end_use_case.execute(200) is True
        
        final_workout = repository.get_by_id(200)
        assert final_workout.status == WorkoutState.COMPLETED

    def test_rest_screen_shows_correct_runner_info(self):
        """Test that rest screen displays correct runner data during rest."""
        base_time = datetime.now().replace(microsecond=0)

        # Load athlete data from CSV
        athlete = load_athletes_from_csv(limit=1)[0]
        
        workout = Workout(
            workout_id=300,
            intervalDistance=400,
            lapsPerInterval=4,
            startMode="INDIVIDUAL"
        )
        
        runner_session = RunnerSession(runner=athlete, restDuration=30)
        workout.add_runner_session(runner_session)
        
        # Initialize repository and save workout
        repository = InMemoryWorkoutRepository()
        repository.save(workout)
        
        # Start workout
        start_use_case = StartWorkoutUseCase(repository)
        start_use_case.execute(300)
        
        # Scan NFC to start running
        scan_nfc_use_case = ScanNFCUseCase(repository)
        scan_nfc_use_case.execute(300, athlete.nfc_tag, base_time.isoformat())
        
        # Record 4 laps to finish interval and move to rest
        scan_rfid_use_case = ScanRFIDUseCase(repository)
        for i in range(4):
            scan_rfid_use_case.execute(
                300,
                athlete.rfid_tag,
                (base_time + timedelta(seconds=5 + i * 5)).isoformat(),
                use_event_time=True,
            )
        
        # Get rest screen
        get_rest_screen_use_case = GetRestScreenUseCase(repository)
        rest_views = get_rest_screen_use_case.execute(300)
        
        assert len(rest_views) == 1
        assert rest_views[0].runner_name == athlete.name
        assert rest_views[0].remaining_rest_seconds > 0

        print("All integration tests passed successfully!")
        print("Pytest percentages (e.g., 55%) show test progress, not a score.")