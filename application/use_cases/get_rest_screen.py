from typing import List
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from application.dto.runner_rest_view import RunnerRestView


class GetRestScreenUseCase:
    """Use case for retrieving the rest screen information of all runners in a workout."""
    
    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int) -> List[RunnerRestView]:
        validate_positive_int(workout_id, "workout_id")
        
        workout = self.workout_repository.get_by_id(workout_id)
        
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")
        
        # Get resting runner sessions from domain
        resting_sessions = workout.get_resting_runner_sessions()
        
        # Update their ready status and convert to DTOs
        views = []
        for session in resting_sessions:
            session.check_if_ready()
            view = RunnerRestView(
                runner_id=session.runner.id,
                runner_name=session.runner.name,
                # Change this from session's job to some UI logic
                # remaining_rest_seconds=session.get_remaining_rest_seconds(),
                is_ready_to_run=session.is_ready()
            )
            views.append(view)
        
        # Sort by remaining seconds, uncomment when doable
        # views.sort(key=lambda v: v.remaining_rest_seconds)
        
        return views
