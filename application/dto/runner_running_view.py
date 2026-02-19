"""
DTO for representing a currently running athlete.
Immutable data transfer object - no business logic.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RunnerRunningView:
    """
    Immutable DTO for a running athlete.
    
    This DTO contains only display data, no behavior.
    Used by controllers to present running athletes to users.
    """
    
    # Runner identification
    runner_id: int
    runner_name: str
    
    # Interval progress
    interval_number: int
    laps_completed: int
    laps_per_interval: int
    
    # Hardware identifiers (useful for display/debug)
    nfc_tag: Optional[str] = None
    rfid_tag: Optional[str] = None
    
    # Timing information (optional)
    start_time: Optional[str] = None
    
    def __post_init__(self):
        """Validate DTO data after initialization."""
        if not self.runner_name:
            raise ValueError("runner_name cannot be empty")
        
        if self.interval_number < 1:
            raise ValueError("interval_number must be positive")
        
        if self.laps_completed < 0:
            raise ValueError("laps_completed cannot be negative")
        
        if self.laps_per_interval < 1:
            raise ValueError("laps_per_interval must be positive")
    
    @property
    def laps_remaining(self) -> int:
        """Calculate remaining laps for current interval."""
        return max(0, self.laps_per_interval - self.laps_completed)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage for current interval."""
        if self.laps_per_interval == 0:
            return 0.0
        return (self.laps_completed / self.laps_per_interval) * 100.0
    
    @property
    def progress_bar(self, width: int = 10) -> str:
        """Generate a simple text progress bar."""
        filled = int((self.laps_completed / self.laps_per_interval) * width)
        empty = width - filled
        return "█" * filled + "░" * empty


# Optional: Add a factory function for creating views
def create_running_view(runner_session, workout) -> RunnerRunningView:
    """
    Factory function to create a RunnerRunningView from domain objects.
    
    Args:
        runner_session: RunnerSession domain object
        workout: Workout domain object
    
    Returns:
        RunnerRunningView DTO
    """
    interval_number = len(runner_session.intervals)
    
    laps_completed = 0
    if runner_session.intervals:
        current_interval = runner_session.intervals[-1]
        laps_completed = len(current_interval.get("laps", []))
    
    return RunnerRunningView(
        runner_id=runner_session.runner.id,
        runner_name=runner_session.runner.name,
        interval_number=interval_number,
        laps_completed=laps_completed,
        laps_per_interval=workout.lapsPerInterval,
        nfc_tag=runner_session.runner.nfc_tag,
        rfid_tag=runner_session.runner.rfid_tag
    )