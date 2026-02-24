from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int, validate_non_empty_string
from application.dto.workout_status_view import WorkoutStatusView
from application.mappers import WorkoutStatusMapper


class ScanNFCUseCase:
    """Use case for handling NFC tag scans to start a runner's interval."""
    
    def __init__(self, workout_repository: WorkoutRepository) -> None:
        self.workout_repository = workout_repository
    
    def execute(self, workout_id: int, nfc_tag_id: str, timestamp: str) -> WorkoutStatusView:
        validate_positive_int(workout_id, "workout_id")
        validate_non_empty_string(nfc_tag_id, "nfc_tag_id")
        validate_non_empty_string(timestamp, "timestamp")
        
        workout = self.workout_repository.get_by_id(workout_id)
        
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with id {workout_id} not found")
        
        workout.record_nfc_start(nfc_tag_id)
        
        self.workout_repository.save(workout)
        
        return WorkoutStatusMapper.from_workout(workout)
