from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout

from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.start_workout import StartWorkoutUseCase
from application.use_cases.scan_nfc import ScanNFCUseCase
from application.use_cases.scan_rfid import ScanRFIDUseCase
from application.use_cases.get_rest_screen import GetRestScreenUseCase
from application.use_cases.end_workout import EndWorkoutUseCase


def main() -> None:
    print("=== Interval Workout Demo ===\n")

    # -----------------------------
    # Create runners
    # -----------------------------
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

    # -----------------------------
    # Create workout
    # -----------------------------
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

    print("Workout created with 2 runners.\n")

    # -----------------------------
    # Start workout
    # -----------------------------
    start_use_case = StartWorkoutUseCase(repository)
    started = start_use_case.execute(100)
    print("Workout started:", started)

    # -----------------------------
    # Simulate NFC scan (start running)
    # -----------------------------
    scan_nfc_use_case = ScanNFCUseCase(repository)
    status = scan_nfc_use_case.execute(100, "NFC001", "2026-02-08T10:00:00")

    print("\nAfter NFC scan:")
    print("Workout ID:", status.workout_id)
    print("Workout State:", status.workout_state)
    print("Active runners:", status.active_runner_count)
    print("Resting runners:", status.resting_runner_count)

    # -----------------------------
    # Simulate RFID laps
    # -----------------------------
    scan_rfid_use_case = ScanRFIDUseCase(repository)

    print("\nSimulating RFID scans...")
    for t in [
        "2026-02-08T10:00:05",
        "2026-02-08T10:00:10",
        "2026-02-08T10:00:15",
        "2026-02-08T10:00:20",
    ]:
        status = scan_rfid_use_case.execute(100, "RFID001", t)
        print(f"RFID at {t} → Active: {status.active_runner_count}, Resting: {status.resting_runner_count}")

    # -----------------------------
    # Get rest screen
    # -----------------------------
    get_rest_screen_use_case = GetRestScreenUseCase(repository)
    rest_views = get_rest_screen_use_case.execute(100)

    print("\nRest Screen:")
    for view in rest_views:
        print(
            f"Runner: {view.runner_name}, "
        )

    # -----------------------------
    # End workout
    # -----------------------------
    end_use_case = EndWorkoutUseCase(repository)
    ended = end_use_case.execute(100)
    print("\nWorkout ended:", ended)

    final_workout = repository.get_by_id(100)
    print("Final workout status:", final_workout.status)

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
