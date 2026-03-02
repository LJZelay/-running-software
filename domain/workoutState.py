"""WorkoutState enum for domain layer."""
from enum import Enum


class WorkoutState(Enum):
    """State of a workout."""
    NOT_STARTED = "NOT_STARTED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
