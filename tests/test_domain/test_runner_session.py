"""Unit tests for RunnerSession domain entity."""
import pytest
import csv
from pathlib import Path
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.runnerState import RunnerState


# Path to actual test data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
ATHLETES_CSV = DATA_DIR / "athletes.csv"


def load_athlete_from_csv(index: int = 0) -> Runner:
    """Load a single athlete from CSV file by index."""
    with open(ATHLETES_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx == index:
                return Runner(
                    runner_id=idx + 1,
                    name=row['name'],
                    email=row['email'],
                    nfc_tag=row['nfc_id'],
                    rfid_tag=row['rfid_id']
                )
    raise ValueError(f"Athlete at index {index} not found")


@pytest.mark.domain
class TestRunnerSessionStateTransitions:
    """Test RunnerSession state management and transitions."""
    
    def test_runner_session_starts_in_not_started_state(self):
        """Test that a new runner session is in NOT_STARTED state."""
        runner = load_athlete_from_csv(0)  # Load Alice
        session = RunnerSession(runner=runner, restDuration=30)
        
        assert session.state == RunnerState.NOT_STARTED
    
    def test_runner_session_can_start_interval(self):
        """Test that a runner session can transition to RUNNING state."""
        runner = load_athlete_from_csv(0)  # Load Alice
        session = RunnerSession(runner=runner, restDuration=30)
        
        session.start_interval()
        
        assert session.state == RunnerState.RUNNING
        assert len(session.intervals) == 1
    
    def test_runner_session_cannot_start_if_already_running(self):
        """Test that a runner cannot start if already running."""
        runner = load_athlete_from_csv(1)  # Load Bob
        session = RunnerSession(runner=runner, restDuration=30)
        
        session.start_interval()
        
        with pytest.raises(ValueError, match="already running"):
            session.start_interval()
    
    def test_runner_session_records_laps(self):
        """Test that laps are recorded while running."""
        runner = load_athlete_from_csv(0)  # Load Alice
        session = RunnerSession(runner=runner, restDuration=30)
        
        session.start_interval()
        session.record_lap()
        session.record_lap()
        
        current_interval = session.intervals[-1]
        assert len(current_interval["laps"]) == 2
    
    def test_runner_session_finishes_interval_after_laps(self):
        """Test that interval finishes when lap count reaches lapsPerInterval."""
        runner = load_athlete_from_csv(2)  # Load Charlie
        session = RunnerSession(runner=runner, restDuration=30)
        
        session.start_interval()
        
        # Record 3 laps and check it doesn't finish
        session.record_lap()
        assert session.should_finish_interval(lapsPerInterval=4) is False
        
        session.record_lap()
        assert session.should_finish_interval(lapsPerInterval=4) is False
        
        session.record_lap()
        assert session.should_finish_interval(lapsPerInterval=4) is False
        
        # 4th lap finishes the interval
        session.record_lap()
        assert session.should_finish_interval(lapsPerInterval=4) is True
    
    def test_runner_session_transitions_to_resting_after_interval(self):
        """Test that runner transitions to RESTING after finishing interval."""
        runner = load_athlete_from_csv(3)  # Load Diana
        session = RunnerSession(runner=runner, restDuration=30)
        
        session.start_interval()
        session.record_lap()
        session.record_lap()
        session.record_lap()
        session.record_lap()
        session.finish_interval()
        
        assert session.state == RunnerState.RESTING
    
    def test_runner_session_cannot_record_lap_while_not_running(self):
        """Test that laps cannot be recorded unless running."""
        runner = load_athlete_from_csv(4)  # Load Eve
        session = RunnerSession(runner=runner, restDuration=30)
        
        with pytest.raises(ValueError, match="Cannot record lap"):
            session.record_lap()

    def test_duplicate_rfid_inside_window_is_ignored(self):
        runner = load_athlete_from_csv(0)
        session = RunnerSession(runner=runner, restDuration=30)

        session.start_interval("2026-02-08T10:00:00")

        first = session.process_rfid_read(
            lapsPerInterval=4,
            timestamp="2026-02-08T10:00:05",
            debounce_ms=200,
        )
        second = session.process_rfid_read(
            lapsPerInterval=4,
            timestamp="2026-02-08T10:00:05.100000",
            debounce_ms=200,
        )

        assert first.decision == "accepted"
        assert second.decision == "ignored"
        assert second.reason == "duplicate_within_window"
        assert len(session.intervals[-1]["laps"]) == 1

    def test_out_of_order_rfid_is_ignored_without_mutation(self):
        runner = load_athlete_from_csv(1)
        session = RunnerSession(runner=runner, restDuration=30)

        session.start_interval("2026-02-08T10:00:00")
        accepted = session.process_rfid_read(
            lapsPerInterval=4,
            timestamp="2026-02-08T10:00:10",
            debounce_ms=200,
        )
        ignored = session.process_rfid_read(
            lapsPerInterval=4,
            timestamp="2026-02-08T10:00:09",
            debounce_ms=200,
        )

        assert accepted.decision == "accepted"
        assert ignored.decision == "ignored"
        assert ignored.reason == "out_of_order_timestamp"
        assert len(session.intervals[-1]["laps"]) == 1

    def test_invalid_timestamp_is_ignored_without_mutation(self):
        runner = load_athlete_from_csv(2)
        session = RunnerSession(runner=runner, restDuration=30)

        session.start_interval("2026-02-08T10:00:00")
        result = session.process_rfid_read(
            lapsPerInterval=4,
            timestamp="not-a-timestamp",
            debounce_ms=200,
        )

        assert result.decision == "ignored"
        assert result.reason == "invalid_timestamp"
        assert len(session.intervals[-1]["laps"]) == 0
