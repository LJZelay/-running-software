from dataclasses import dataclass


@dataclass
class WorkoutConfig:
	interval_distance: int = 400
	rest_time_seconds: int = 60
	laps_per_interval: int = 1

