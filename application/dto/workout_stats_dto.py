from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class WorkoutStatsDTO:
    """Aggregate statistics for the whole workout."""
    total_runners: int
    intervals_completed: Dict[int, int]  # interval number -> count of runners who completed it
    average_pace_per_interval: Dict[int, float]  # interval number -> average pace across runners
    # Additional stats can be added later