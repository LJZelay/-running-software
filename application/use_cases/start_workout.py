from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int


class StartWorkoutUseCase:
    """Use case for starting a workout."""
    
    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int, timestamp: str = None, use_event_time: bool = False) -> bool:
        validate_positive_int(workout_id, "workout_id")
        
        workout = self.workout_repository.get_by_id(workout_id)
        
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")
        
        event_timestamp = timestamp if use_event_time else None
        result = workout.start(event_timestamp)
        
        if result:
            self.workout_repository.save(workout)
        
        return result
