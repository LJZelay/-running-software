from abc import ABC, abstractmethod
from typing import Optional #Abstract base class for the WorkoutRepository, defining the interface for accessing workout data.


class WorkoutRepository(ABC):
    
    @abstractmethod
    def get_by_id(self, workout_id: int) -> Optional[object]:
        pass
    
    @abstractmethod
    def save(self, workout: object) -> None:
        pass
