"""
Use case for group start - starting all eligible runners in a workout simultaneously.
Implementation delegates to domain instead of inspecting state internally.
"""
from typing import Tuple
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from domain.runnerState import RunnerState


class GroupStartUseCase:
    """Use case for starting all eligible runners in a workout at once."""
    
    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int) -> Tuple[int, int, int]:
        """
        Start all eligible runners in the workout.
        
        Args:
            workout_id: ID of the workout
        
        Returns:
            Tuple of (started_count, active_count, resting_count)
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        validate_positive_int(workout_id, "workout_id")
        
        # Get workout
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        # Check if there are any runners
        if not workout.runnerSessions:
            raise ValueError("Cannot start group: No runners in workout")
        
        # Start workout if not already active
        if workout.is_not_started():
            workout.start()
        
        # Only proceed if workout is active
        if not workout.is_active():
            raise ValueError(f"Cannot start group: Workout is {workout.status.value}")
        
        # Start all eligible runners (NOT_STARTED or READY)
        started_count = 0
        for runner_session in workout.runnerSessions:
            if runner_session.is_not_started() or runner_session.is_ready():
                try:
                    runner_session.start_interval()
                    started_count += 1
                except ValueError:
                    # Skip if runner cannot be started for any reason
                    continue
        
        # Save updated workout
        self.workout_repository.save(workout)
        
        # Get current counts
        active_count, resting_count = workout.get_runner_counts()
        
        return started_count, active_count, resting_count
