from enum import Enum

class RunnerState(Enum):
    NOT_STARTED = "NOT_STARTED"
    READY = "READY"
    RUNNING = "RUNNING"
    RESTING = "RESTING"