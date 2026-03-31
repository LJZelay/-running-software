from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class IntervalDetail:
    """Detailed data for one interval of a runner."""
    interval_number: int
    start: str          # ISO timestamp
    end: str
    duration_ms: int    # in milliseconds
    pace_per_km: float  # seconds per kilometer (or per configured unit)
    splits_ms: List[int]  # split times in milliseconds (between consecutive laps)


@dataclass(frozen=True)
class RunnerAnalyticsDTO:
    """Analytics data for a single runner."""
    runner_id: int
    runner_name: str
    intervals: List[IntervalDetail]
    overall_avg_pace: float   # seconds per kilometer across all intervals
    rest_efficiency: Optional[float] = None  # (actual_rest_total / configured_rest_total) if rests recorded