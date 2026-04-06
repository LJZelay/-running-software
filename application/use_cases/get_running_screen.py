"""
Use case for getting the list of currently running athletes.
Implementation uses domain query methods instead of inspecting state internally.
"""
from typing import List
from application.dto.runner_running_view import RunnerRunningView
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from domain.runnerState import RunnerState


class GetRunningScreenUseCase:
    """Use case for retrieving currently running athletes."""
    
    def __init__(self, workout_repository: WorkoutRepository):
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
        validate_positive_int(workout_id, "workout_id")
        
        workout = self.workout_repository.get_by_id(workout_id)
        if not workout:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")
        
        running_views = []
        
        # Compute running sessions from the workout sessions directly.
        running_sessions = [rs for rs in workout.runnerSessions if rs.state == RunnerState.RUNNING]

        for runner_session in running_sessions:
            # Get current interval metadata from domain
            interval_number = len(runner_session.intervals)
            
            # Get laps completed for current interval
            laps_completed = 0
            if runner_session.intervals:
                current_interval = runner_session.intervals[-1]
                laps_completed = current_interval.lap_count()
            
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
