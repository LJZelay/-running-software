"""
Use case for adding a runner to a workout.
Implementation uses domain entity abstraction instead of inspecting state.
"""
from typing import Optional
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int


class AddRunnerToWorkoutUseCase:
    """Use case for adding a runner to an existing workout."""
    
    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int, runner: Runner, rest_duration: int = 60) -> bool:
        """
        Add a runner to a workout by creating a RunnerSession.
        
        Args:
            workout_id: ID of the workout
            runner: Runner domain object
            rest_duration: Rest time in seconds (default: 60)
        
        Returns:
            True if successfully added, False otherwise
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        validate_positive_int(workout_id, "workout_id")
        
        if not runner:
            raise ValueError("Runner cannot be None")
        
        if rest_duration < 0:
            raise ValueError("rest_duration cannot be negative")
        
        # Get workout
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        # Check if workout already started - delegate to domain
        if not workout.is_not_started():
            return False
        
        # Check for duplicate NFC tag
        existing = workout._find_runner_session_by_nfc(runner.nfc_tag)
        if existing:
            raise ValueError(f"Runner with NFC tag {runner.nfc_tag} already exists")
        
        # Check for duplicate RFID tag
        existing = workout._find_runner_session_by_rfid(runner.rfid_tag)
        if existing:
            raise ValueError(f"Runner with RFID tag {runner.rfid_tag} already exists")
        
        # Create runner session and add to workout
        runner_session = RunnerSession(
            runner=runner,
            restDuration=rest_duration
        )
        
        added = workout.add_runner_session(runner_session)
        
        if added:
            self.workout_repository.save(workout)
        
        return added
    
    def execute_by_nfc(self, workout_id: int, nfc_tag: str) -> Optional[Runner]:
        """
        Find a runner by NFC tag without adding them.
        
        Args:
            workout_id: ID of the workout
            nfc_tag: NFC tag to search for
        
        Returns:
            Runner if found, None otherwise
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        validate_positive_int(workout_id, "workout_id")
        
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        runner_session = workout._find_runner_session_by_nfc(nfc_tag)
        return runner_session.runner if runner_session else None
