"""
Use case for getting the list of currently running athletes.
Simple implementation that works with existing domain models.
"""
from typing import List
from domain.workout import Workout
from application.dto.runner_running_view import RunnerRunningView
from application.repositories.in_memory_workout_repository import InMemoryWorkoutRepository
from application.exceptions import WorkoutNotFoundError, InvalidApplicationRequestError


class GetRunningScreenUseCase:
    """Use case for retrieving currently running athletes."""
    
    def __init__(self, workout_repository: InMemoryWorkoutRepository):
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int) -> List[RunnerRunningView]:
        """
        Get list of currently running athletes.
        
        Args:
            workout_id: ID of the workout
        
        Returns:
            List of RunnerRunningView DTOs, sorted by name
        
        Raises:
            WorkoutNotFoundError: If workout doesn't exist
        """
        # Validate input
        if not isinstance(workout_id, int) or workout_id <= 0:
            raise InvalidApplicationRequestError("workout_id must be a positive integer")
        
        # Get workout
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        running_views = []
        
        # Find all runner sessions in RUNNING state
        for runner_session in workout.runnerSessions:
            if runner_session.state == "RUNNING":
                # Get current interval number
                interval_number = len(runner_session.intervals)
                
                # Get laps completed for current interval
                laps_completed = 0
                if runner_session.intervals:
                    current_interval = runner_session.intervals[-1]
                    laps_completed = len(current_interval.get("laps", []))
                
                # Create view DTO
                view = RunnerRunningView(
                    runner_id=runner_session.runner.id,
                    runner_name=runner_session.runner.name,
                    interval_number=interval_number,
                    laps_completed=laps_completed,
                    laps_per_interval=workout.lapsPerInterval,
                    nfc_tag=runner_session.runner.nfc_tag,
                    rfid_tag=runner_session.runner.rfid_tag
                )
                running_views.append(view)
        
        # Sort by runner name
        running_views.sort(key=lambda v: v.runner_name)
        
        return running_views
    
    def get_running_count(self, workout_id: int) -> int:
        """
        Get count of currently running athletes.
        
        Args:
            workout_id: ID of the workout
        
        Returns:
            Number of runners in RUNNING state
        """
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            return 0
        
        count = sum(1 for rs in workout.runnerSessions if rs.state == "RUNNING")
        return count