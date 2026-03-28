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
from application.rfid_contracts import RFIDDecision, RFIDReason


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

    def test_replay_determinism_same_ordered_stream_same_outcome(self):
        """Same ordered RFID stream replayed twice yields identical decisions and state."""
        athlete = load_athletes_from_csv(limit=1)[0]

        def run_stream(workout_id: int):
            workout = Workout(
                workout_id=workout_id,
                intervalDistance=400,
                lapsPerInterval=4,
                startMode="INDIVIDUAL",
            )
            workout.add_runner_session(RunnerSession(runner=athlete, restDuration=30))

            repository = InMemoryWorkoutRepository()
            repository.save(workout)

            StartWorkoutUseCase(repository).execute(workout_id)
            ScanNFCUseCase(repository).execute(workout_id, athlete.nfc_tag, "2026-02-08T10:00:00")
            scan_rfid_use_case = ScanRFIDUseCase(repository)

            stream = [
                "2026-02-08T10:00:05",  # accepted
                "2026-02-08T10:00:05",  # duplicate (equal timestamp)
                "2026-02-08T10:00:07",  # accepted
                "2026-02-08T10:00:06",  # out-of-order
                "2026-02-08T10:00:09",  # accepted
                "2026-02-08T10:00:11",  # accepted -> interval finish
            ]

            decisions: list[tuple[str, str, int, int]] = []
            for ts in stream:
                result = scan_rfid_use_case.execute(
                    workout_id,
                    athlete.rfid_tag,
                    ts,
                    use_event_time=True,
                )
                decisions.append(
                    (
                        result.decision.value,
                        result.reason.value,
                        result.active_runner_count,
                        result.resting_runner_count,
                    )
                )

            reloaded = repository.get_by_id(workout_id)
            rs = reloaded.runnerSessions[0]
            snapshot = {
                "state": rs.state.value,
                "interval_count": len(rs.intervals),
                "rest_count": len(rs.rests),
                "lap_count": len(rs.intervals[0]["laps"]),
                "last_accepted": rs.lastAcceptedRfidEpochMs,
            }
            return decisions, snapshot

        decisions1, snapshot1 = run_stream(401)
        decisions2, snapshot2 = run_stream(402)

        assert decisions1 == decisions2
        assert snapshot1 == snapshot2

    def test_ignored_rfid_events_do_not_mutate_runner_state(self):
        """Ignored RFID events (duplicate/out-of-order/invalid) should not mutate lap state."""
        athlete = load_athletes_from_csv(limit=1)[0]
        workout_id = 403

        workout = Workout(
            workout_id=workout_id,
            intervalDistance=400,
            lapsPerInterval=4,
            startMode="INDIVIDUAL",
        )
        workout.add_runner_session(RunnerSession(runner=athlete, restDuration=30))

        repository = InMemoryWorkoutRepository()
        repository.save(workout)

        StartWorkoutUseCase(repository).execute(workout_id)
        ScanNFCUseCase(repository).execute(workout_id, athlete.nfc_tag, "2026-02-08T10:00:00")
        scan_rfid_use_case = ScanRFIDUseCase(repository)

        accepted = scan_rfid_use_case.execute(
            workout_id,
            athlete.rfid_tag,
            "2026-02-08T10:00:05",
            use_event_time=True,
        )
        assert accepted.decision == RFIDDecision.ACCEPTED
        assert accepted.reason == RFIDReason.VALID_FINISH

        rs_before = repository.get_by_id(workout_id).runnerSessions[0]
        lap_count_before = len(rs_before.intervals[0]["laps"])
        last_accepted_before = rs_before.lastAcceptedRfidEpochMs

        duplicate = scan_rfid_use_case.execute(
            workout_id,
            athlete.rfid_tag,
            "2026-02-08T10:00:05",
            use_event_time=True,
        )
        out_of_order = scan_rfid_use_case.execute(
            workout_id,
            athlete.rfid_tag,
            "2026-02-08T10:00:04",
            use_event_time=True,
        )
        invalid = scan_rfid_use_case.execute(
            workout_id,
            athlete.rfid_tag,
            "not-a-timestamp",
            use_event_time=True,
        )

        assert duplicate.decision == RFIDDecision.IGNORED
        assert duplicate.reason == RFIDReason.DUPLICATE_WITHIN_WINDOW
        assert out_of_order.decision == RFIDDecision.IGNORED
        assert out_of_order.reason == RFIDReason.OUT_OF_ORDER_TIMESTAMP
        assert invalid.decision == RFIDDecision.IGNORED
        assert invalid.reason == RFIDReason.INVALID_TIMESTAMP

        rs_after = repository.get_by_id(workout_id).runnerSessions[0]
        assert len(rs_after.intervals[0]["laps"]) == lap_count_before
        assert rs_after.lastAcceptedRfidEpochMs == last_accepted_before

    def test_csv_event_stream_simulation_replay_is_stable(self):
        """Use current CSV data to simulate a connection-like replay and validate stable outcomes."""

        def run_replay(workout_id: int):
            athletes = load_athletes_from_csv(limit=6)
            workout = Workout(
                workout_id=workout_id,
                intervalDistance=400,
                lapsPerInterval=1,
                startMode="GROUP",
            )
            for athlete in athletes:
                workout.add_runner_session(RunnerSession(runner=athlete, restDuration=30))

            repository = InMemoryWorkoutRepository()
            repository.save(workout)

            start_uc = StartWorkoutUseCase(repository)
            scan_nfc_uc = ScanNFCUseCase(repository)
            scan_rfid_uc = ScanRFIDUseCase(repository)

            group_tags: list[str] = []
            accepted_rfid = 0
            ignored_rfid = 0

            with open(DATA_DIR / "events.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    if idx >= 30:
                        break

                    event_type = row["TYPE"].strip().upper()
                    ts_iso = datetime.fromtimestamp(int(row["TIMESTAMP"]) / 1000.0).isoformat()
                    tag = (row.get("TAG") or "").strip()

                    if event_type == "GROUP" and tag:
                        group_tags.append(tag)
                    elif event_type == "START":
                        start_uc.execute(workout_id)
                        group_tags.clear()
                    elif event_type == "NFC" and tag:
                        scan_nfc_uc.execute(workout_id, tag, ts_iso, use_event_time=True)
                    elif event_type == "RFID" and tag:
                        result = scan_rfid_uc.execute(workout_id, tag, ts_iso, use_event_time=True)
                        if result.decision == RFIDDecision.ACCEPTED:
                            accepted_rfid += 1
                        else:
                            ignored_rfid += 1

            final_workout = repository.get_by_id(workout_id)
            active, resting = final_workout.get_runner_counts()
            snapshot = {
                "accepted": accepted_rfid,
                "ignored": ignored_rfid,
                "active": active,
                "resting": resting,
                "status": final_workout.status.value,
            }
            return snapshot

        first = run_replay(500)
        second = run_replay(501)

        assert first == second
        assert first["accepted"] > 0