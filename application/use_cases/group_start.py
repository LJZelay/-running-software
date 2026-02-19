"""
Use case for group start - starting all eligible runners in a workout simultaneously.
Simple implementation that works with existing domain models.
"""
from typing import Tuple
from domain.workout import Workout
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.exceptions import WorkoutNotFoundError, InvalidApplicationRequestError


class GroupStartUseCase:
    """Use case for starting all eligible runners in a workout at once."""
    
    def __init__(self, workout_repository: InMemoryWorkoutRepository):
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
            InvalidApplicationRequestError: If group start cannot be performed
        """
        # Validate input
        if not isinstance(workout_id, int) or workout_id <= 0:
            raise InvalidApplicationRequestError("workout_id must be a positive integer")
        
        # Get workout
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        # Check if there are any runners
        if not workout.runnerSessions:
            raise InvalidApplicationRequestError("Cannot start group: No runners in workout")
        
        # Start workout if not already active
        if workout.status == "NOT_STARTED":
            workout.start()
        
        # Only proceed if workout is active
        if workout.status != "ACTIVE":
            raise InvalidApplicationRequestError(f"Cannot start group: Workout is {workout.status}")
        
        # Start all eligible runners (NOT_STARTED or READY)
        started_count = 0
        for runner_session in workout.runnerSessions:
            if runner_session.state in ["NOT_STARTED", "READY"]:
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
    
    def get_eligible_count(self, workout_id: int) -> int:
        """
        Get count of runners eligible to start.
        
        Args:
            workout_id: ID of the workout
        
        Returns:
            Number of runners in NOT_STARTED or READY state
        """
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            return 0
        
        count = sum(1 for rs in workout.runnerSessions 
                   if rs.state in ["NOT_STARTED", "READY"])
        return count