from typing import Dict
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from application.dto.workout_stats_dto import WorkoutStatsDTO
from application.use_cases.get_runner_analytics import GetRunnerAnalyticsUseCase


class GetWorkoutStatsUseCase:
    """Compute aggregated workout statistics."""

    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository
        self.analytics_use_case = GetRunnerAnalyticsUseCase(workout_repository)

    def execute(self, workout_id: int) -> WorkoutStatsDTO:
        validate_positive_int(workout_id, "workout_id")
        workout = self.workout_repository.get_by_id(workout_id)
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")

        total_runners = len(workout.runnerSessions)

        # intervals_completed: interval number -> count of runners who completed it
        intervals_completed: Dict[int, int] = {}
        average_pace_per_interval: Dict[int, float] = {}
        pace_sums: Dict[int, float] = {}
        pace_counts: Dict[int, int] = {}

        runner_analytics = self.analytics_use_case.execute(workout_id)
        for ra in runner_analytics:
            for interval in ra.intervals:
                num = interval.interval_number
                intervals_completed[num] = intervals_completed.get(num, 0) + 1
                # accumulate pace for average later
                if interval.pace_per_km is not None:
                    pace_sums[num] = pace_sums.get(num, 0.0) + interval.pace_per_km
                    pace_counts[num] = pace_counts.get(num, 0) + 1
        for num in pace_sums:
            average_pace_per_interval[num] = pace_sums[num] / pace_counts[num]

        return WorkoutStatsDTO(
            total_runners=total_runners,
            intervals_completed=intervals_completed,
            average_pace_per_interval=average_pace_per_interval
        )