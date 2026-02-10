from typing import List
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from application.dto.runner_rest_view import RunnerRestView


class GetRestScreenUseCase:
    
    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int) -> List[RunnerRestView]:
        validate_positive_int(workout_id, "workout_id")
        
        workout = self.workout_repository.get_by_id(workout_id)
        
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")
        
        rest_data = workout.get_rest_screen()
        
        views = []
        for data in rest_data:
            view = RunnerRestView(
                runner_id=data["runner_id"],
                runner_name=data["runner_name"],
                remaining_rest_seconds=data["remaining_seconds"],
                is_ready_to_run=(data["remaining_seconds"] <= 0)
            )
            views.append(view)
        
        return views
