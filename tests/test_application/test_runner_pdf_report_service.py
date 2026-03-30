from pathlib import Path

from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.use_cases.generate_runner_report import GenerateRunnerReportUseCase
from application.use_cases.end_workout import EndWorkoutUseCase
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from domain.workoutState import WorkoutState
from externalInterface.runner_pdf_report_service import RunnerPdfReportService


def _build_runner(runner_id: int, name: str) -> Runner:
    return Runner(
        runner_id=runner_id,
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        nfc_tag=f"NFC{runner_id}",
        rfid_tag=f"RFID{runner_id}",
    )


def test_end_workout_generates_one_pdf_per_runner(tmp_path: Path) -> None:
    workout = Workout(
        workout_id=901,
        intervalDistance=400,
        lapsPerInterval=2,
        startMode="INDIVIDUAL",
    )

    alice = RunnerSession(runner=_build_runner(1, "Alice"), restDuration=30)
    bob = RunnerSession(runner=_build_runner(2, "Bob"), restDuration=45)

    alice.intervals = [
        {
            "intervalNumber": 1,
            "start": "2026-03-30T10:00:00",
            "laps": ["2026-03-30T10:01:00", "2026-03-30T10:02:00"],
            "end": "2026-03-30T10:02:00",
        }
    ]
    alice.rests = [
        {
            "start": "2026-03-30T10:02:00",
            "restDuration": 30,
            "end": "2026-03-30T10:02:28",
        }
    ]

    bob.intervals = [
        {
            "intervalNumber": 1,
            "start": "2026-03-30T10:00:10",
            "laps": ["2026-03-30T10:01:10", "2026-03-30T10:02:20"],
            "end": "2026-03-30T10:02:20",
        }
    ]
    bob.rests = [
        {
            "start": "2026-03-30T10:02:20",
            "restDuration": 45,
            "end": "2026-03-30T10:03:10",
        }
    ]

    workout.add_runner_session(alice)
    workout.add_runner_session(bob)
    workout.start("2026-03-30T10:00:00")

    repository = InMemoryWorkoutRepository()
    repository.save(workout)
    report_service = RunnerPdfReportService(output_dir=tmp_path)
    generate_report_use_case = GenerateRunnerReportUseCase(report_service)
    use_case = EndWorkoutUseCase(repository, generate_report_use_case=generate_report_use_case)

    ended = use_case.execute(901)

    assert ended is True
    saved = repository.get_by_id(901)
    assert saved.status == WorkoutState.COMPLETED

    reports = list(tmp_path.glob("*.pdf"))
    assert len(reports) == 2

    alice_report = next(path for path in reports if "runner_1_Alice" in path.name)
    bob_report = next(path for path in reports if "runner_2_Bob" in path.name)

    alice_text = alice_report.read_bytes().decode("latin-1", errors="ignore")
    bob_text = bob_report.read_bytes().decode("latin-1", errors="ignore")

    assert "Runner: Alice" in alice_text
    assert "Configured Rest Duration: 30 s" in alice_text
    assert "duration=120000 ms" in alice_text
    assert "actual=28000 ms" in alice_text
    assert "Runner: Bob" not in alice_text

    assert "Runner: Bob" in bob_text
    assert "Configured Rest Duration: 45 s" in bob_text
    assert "duration=130000 ms" in bob_text
    assert "actual=50000 ms" in bob_text
    assert "Runner: Alice" not in bob_text


def test_report_handles_runner_with_no_completed_intervals(tmp_path: Path) -> None:
    workout = Workout(
        workout_id=902,
        intervalDistance=800,
        lapsPerInterval=2,
        startMode="INDIVIDUAL",
    )

    runner_session = RunnerSession(runner=_build_runner(3, "Carol"), restDuration=60)
    workout.add_runner_session(runner_session)
    workout.start("2026-03-30T11:00:00")

    repository = InMemoryWorkoutRepository()
    repository.save(workout)
    report_service = RunnerPdfReportService(output_dir=tmp_path)
    generate_report_use_case = GenerateRunnerReportUseCase(report_service)
    use_case = EndWorkoutUseCase(repository, generate_report_use_case=generate_report_use_case)

    assert use_case.execute(902) is True

    reports = list(tmp_path.glob("*.pdf"))
    assert len(reports) == 1
    report_text = reports[0].read_bytes().decode("latin-1", errors="ignore")
    assert "Runner: Carol" in report_text
    assert "No intervals were completed in this workout." in report_text


def test_report_never_shows_negative_durations(tmp_path: Path) -> None:
    workout = Workout(
        workout_id=903,
        intervalDistance=400,
        lapsPerInterval=1,
        startMode="INDIVIDUAL",
    )
    runner_session = RunnerSession(runner=_build_runner(4, "Dana"), restDuration=30)
    runner_session.intervals = [
        {
            "intervalNumber": 1,
            "start": "2026-03-30T13:51:14.453929",
            "laps": ["2023-12-31T18:01:52"],
            "end": "2023-12-31T18:01:52",
        }
    ]
    workout.add_runner_session(runner_session)
    workout.start("2026-03-30T13:51:00")

    repository = InMemoryWorkoutRepository()
    repository.save(workout)
    report_service = RunnerPdfReportService(output_dir=tmp_path)
    generate_report_use_case = GenerateRunnerReportUseCase(report_service)
    use_case = EndWorkoutUseCase(repository, generate_report_use_case=generate_report_use_case)

    assert use_case.execute(903) is True

    report_text = next(tmp_path.glob("*.pdf")).read_bytes().decode("latin-1", errors="ignore")
    assert "duration=-" not in report_text
    assert "split=-" not in report_text
    assert "duration=N/A" in report_text
