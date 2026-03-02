"""RunnerState enum for domain layer."""
from enum import Enum


class RunnerState(Enum):
    """State of a runner during a workout."""
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    RESTING = "RESTING"
    READY = "READY"
