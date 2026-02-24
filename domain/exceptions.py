# domain/exceptions.py
# clarity and error handling
# better communication of issues 

class DomainError(Exception):
    """Base class for domain-specific exceptions."""
    pass

class WorkoutNotActiveError(DomainError):
    """Raised when an action is attempted on a workout that is not active."""
    pass

class WorkoutCompletedError(DomainError):
    """Raised when an action is attempted on a workout that has already been completed."""
    pass

class UnknownTagError(DomainError):
    """Raised when an NFC tag is scanned that does not correspond to any known runner."""
    pass

class InvalidRunnerStateError(DomainError):
    """Raised when an action is attempted that is not valid for the runner's current state."""
    pass

class DuplicateRunnerError(DomainError):
    """Raised when an attempt is made to add a runner that already exists."""
    pass