from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from application.use_cases.generate_runner_report import GenerateRunnerReportUseCase
from typing import Optional


class EndWorkoutUseCase:
    """Use case for ending a workout."""
    
    def __init__(
        self,
        workout_repository: WorkoutRepository,
        generate_report_use_case: Optional[GenerateRunnerReportUseCase] = None,
    ) -> None:
        self.workout_repository = workout_repository
        self.generate_report_use_case = generate_report_use_case
    
    def execute(self, workout_id: int) -> bool:
        validate_positive_int(workout_id, "workout_id")
        
        workout = self.workout_repository.get_by_id(workout_id)
        
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")
        
        result = workout.end()
        
        if result:
            self.workout_repository.save(workout)
            if self.generate_report_use_case is not None:
                # Generate one report per runner when the workout is finalized.
                self.generate_report_use_case.execute(workout)
        
        return result

# This use case handles the logic for ending a workout. It validates the input, retrieves the workout from the repository, calls the end method on the workout, and saves the updated workout back to the repository if it was successfully ended.
