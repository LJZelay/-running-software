from abc import ABC, abstractmethod
from typing import Optional #Abstract base class for the WorkoutRepository, defining the interface for accessing workout data.


class WorkoutRepository(ABC):
    
    @abstractmethod
    def get_by_id(self, workout_id: int) -> Optional[object]:
        pass
    
    @abstractmethod
    def save(self, workout: object) -> None:
        pass

    def get_with_sessions(self, workout_id: int) -> Optional[object]:
        """Default implementation returns the same as get_by_id."""
        return self.get_by_id(workout_id)
