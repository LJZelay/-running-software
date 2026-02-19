"""
Use case for adding a runner to a workout.
Simple implementation that works with existing domain models.
"""
from typing import Optional
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.workout import Workout
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.exceptions import WorkoutNotFoundError, InvalidApplicationRequestError


class AddRunnerToWorkoutUseCase:
    """Use case for adding a runner to an existing workout."""
    
    def __init__(self, workout_repository: InMemoryWorkoutRepository):
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int, runner: Runner, rest_duration: int = 60) -> Workout:
        """
        Add a runner to a workout by creating a RunnerSession.
        
        Args:
            workout_id: ID of the workout
            runner: Runner domain object
            rest_duration: Rest time in seconds (default: 60)
        
        Returns:
            Updated Workout object
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
            InvalidApplicationRequestError: If runner cannot be added
        """
        # Validate inputs
        if not isinstance(workout_id, int) or workout_id <= 0:
            raise InvalidApplicationRequestError("workout_id must be a positive integer")
        
        if not runner:
            raise InvalidApplicationRequestError("Runner cannot be None")
        
        if rest_duration < 0:
            raise InvalidApplicationRequestError("rest_duration cannot be negative")
        
        # Get workout
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        # Check if workout already started
        if workout.status != "NOT_STARTED":
            raise InvalidApplicationRequestError(f"Cannot add runner: workout is {workout.status}")
        
        # Check for duplicate NFC tag
        existing = workout._find_runner_session_by_nfc(runner.nfc_tag)
        if existing:
            raise InvalidApplicationRequestError(f"Runner with NFC tag {runner.nfc_tag} already exists")
        
        # Check for duplicate RFID tag
        existing = workout._find_runner_session_by_rfid(runner.rfid_tag)
        if existing:
            raise InvalidApplicationRequestError(f"Runner with RFID tag {runner.rfid_tag} already exists")
        
        # Create runner session and add to workout
        runner_session = RunnerSession(
            runner=runner,
            restDuration=rest_duration,
            state="NOT_STARTED"
        )
        
        workout.add_runner_session(runner_session)
        
        # Save updated workout
        self.workout_repository.save(workout)
        
        return workout
    
    def execute_by_nfc(self, workout_id: int, nfc_tag: str) -> Optional[Runner]:
        """
        Find a runner by NFC tag without adding them.
        Used for Option 2: Add athlete to group (verification).
        
        Args:
            workout_id: ID of the workout
            nfc_tag: NFC tag to search for
        
        Returns:
            Runner if found, None otherwise
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        runner_session = workout._find_runner_session_by_nfc(nfc_tag)
        return runner_session.runner if runner_session else None