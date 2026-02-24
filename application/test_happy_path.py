from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from domain.workout_state import WorkoutState
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.start_workout import StartWorkoutUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.end_workout import EndWorkoutUseCase

# This test simulates a happy path scenario for an interval workout. It creates a workout with two runners, starts the workout, simulates NFC and RFID scans for one runner, checks the rest screen data, ends the workout, and verifies that the workout status is updated to COMPLETED.

def test_happy_path_interval_workout() -> None:
    runner1 = Runner(
        runner_id=1,
        name="Alice",
        email="alice@example.com",
        nfc_tag="NFC001",
        rfid_tag="RFID001"
    )
    
    runner2 = Runner(
        runner_id=2,
        name="Bob",
        email="bob@example.com",
        nfc_tag="NFC002",
        rfid_tag="RFID002"
    )
    
    workout = Workout(
        workout_id=100,
        intervalDistance=400,
        lapsPerInterval=4,
        startMode="INDIVIDUAL"
    )
    
    rs1 = RunnerSession(runner=runner1, restDuration=30)
    rs2 = RunnerSession(runner=runner2, restDuration=30)
    
    workout.add_runner_session(rs1)
    workout.add_runner_session(rs2)
    
    repository = InMemoryWorkoutRepository()
    repository.save(workout)
    
    start_use_case = StartWorkoutUseCase(repository)
    started = start_use_case.execute(100)
    assert started == True
    
    scan_nfc_use_case = ScanNFCUseCase(repository)
    status1 = scan_nfc_use_case.execute(100, "NFC001", "2026-02-08T10:00:00")
    assert status1.workout_id == 100
    assert status1.workout_state == WorkoutState.ACTIVE.value
    assert status1.active_runner_count == 1
    assert status1.resting_runner_count == 0
    
    scan_rfid_use_case = ScanRFIDUseCase(repository)
    status2 = scan_rfid_use_case.execute(100, "RFID001", "2026-02-08T10:00:05")
    assert status2.workout_id == 100
    
    status3 = scan_rfid_use_case.execute(100, "RFID001", "2026-02-08T10:00:10")
    assert status3.workout_id == 100
    
    status4 = scan_rfid_use_case.execute(100, "RFID001", "2026-02-08T10:00:15")
    assert status4.workout_id == 100
    
    status5 = scan_rfid_use_case.execute(100, "RFID001", "2026-02-08T10:00:20")
    assert status5.active_runner_count == 0
    assert status5.resting_runner_count == 1
    
    get_rest_screen_use_case = GetRestScreenUseCase(repository)
    rest_views = get_rest_screen_use_case.execute(100)
    assert len(rest_views) == 1
    assert rest_views[0].runner_name == "Alice"
    assert rest_views[0].remaining_rest_seconds > 0
    
    end_use_case = EndWorkoutUseCase(repository)
    ended = end_use_case.execute(100)
    assert ended == True
    
    final_workout = repository.get_by_id(100)
    assert final_workout.status == WorkoutState.COMPLETED


if __name__ == "__main__":
    try:
        test_happy_path_interval_workout()
        print("✓ Happy path test PASSED")
    except Exception as e:
        print(f"✗ Happy path test FAILED: {e}")
        import traceback
        traceback.print_exc()

