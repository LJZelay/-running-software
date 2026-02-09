from typing import Optional, Dict
from application.repositories.workout_repository import WorkoutRepository #In-memory implementation of the WorkoutRepository interface for testing purposes.


class InMemoryWorkoutRepository(WorkoutRepository):
    
    def __init__(self) -> None:
        self._storage: Dict[int, object] = {}
    
    def get_by_id(self, workout_id: int) -> Optional[object]:
        return self._storage.get(workout_id)
    
    def save(self, workout: object) -> None:
        self._storage[workout.workout_id] = workout
    
    def clear(self) -> None:
        self._storage.clear()
