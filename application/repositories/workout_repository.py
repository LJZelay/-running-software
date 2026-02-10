from abc import ABC, abstractmethod
from typing import Optional


class WorkoutRepository(ABC):
    
    @abstractmethod
    def get_by_id(self, workout_id: int) -> Optional[object]:
        pass
    
    @abstractmethod
    def save(self, workout: object) -> None:
        pass
