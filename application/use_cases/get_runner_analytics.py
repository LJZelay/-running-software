from typing import List
from application.repositories.workout_repository import WorkoutRepository
from application.exceptions import WorkoutNotFoundError
from application.input_validation import validate_positive_int
from application.dto.runner_analytics_dto import RunnerAnalyticsDTO, IntervalDetail
from domain.runnerSession import RunnerSession
from datetime import datetime


class GetRunnerAnalyticsUseCase:
    """Compute analytics for each runner in a workout."""

    def __init__(self, workout_repository: WorkoutRepository):
        self.workout_repository = workout_repository

    def execute(self, workout_id: int) -> List[RunnerAnalyticsDTO]:
        validate_positive_int(workout_id, "workout_id")
        workout = self.workout_repository.get_with_sessions(workout_id)
        if workout is None:
            raise WorkoutNotFoundError(f"Workout with ID {workout_id} not found")

        interval_distance = workout.intervalDistance  # in meters
        if interval_distance <= 0:
            raise ValueError("Invalid interval distance")

        results = []
        for rs in workout.runnerSessions:
            intervals_detail = []
            total_duration_ms = 0
            for interval in rs.intervals:
                start = interval.get("start")
                end = interval.get("end")
                if not start or not end:
                    continue
                try:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                except ValueError:
                    continue
                duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
                total_duration_ms += duration_ms

                # Pace = duration per distance (convert to seconds per km)
                duration_sec = duration_ms / 1000.0
                distance_km = interval_distance / 1000.0
                pace_per_km = duration_sec / distance_km if distance_km > 0 else 0.0

                # Split times (laps)
                laps = interval.get("laps", [])
                splits_ms = []
                prev = start
                for lap in laps:
                    if not lap:
                        continue
                    try:
                        lap_dt = datetime.fromisoformat(lap)
                        prev_dt = datetime.fromisoformat(prev) if isinstance(prev, str) else prev
                        split_ms = int((lap_dt - prev_dt).total_seconds() * 1000)
                        splits_ms.append(split_ms)
                        prev = lap
                    except (ValueError, TypeError):
                        pass

                intervals_detail.append(IntervalDetail(
                    interval_number=interval.get("intervalNumber", len(intervals_detail)+1),
                    start=start,
                    end=end,
                    duration_ms=duration_ms,
                    pace_per_km=pace_per_km,
                    splits_ms=splits_ms
                ))

            # Overall average pace (weighted by duration)
            if intervals_detail:
                total_pace = sum(i.pace_per_km for i in intervals_detail)
                overall_avg_pace = total_pace / len(intervals_detail)
            else:
                overall_avg_pace = 0.0

            # Rest efficiency (optional)
            rest_efficiency = None
            if rs.rests:
                total_actual_rest_ms = 0
                total_configured_rest_ms = 0
                for rest in rs.rests:
                    start = rest.get("start")
                    end = rest.get("end")
                    if start and end:
                        try:
                            start_dt = datetime.fromisoformat(start)
                            end_dt = datetime.fromisoformat(end)
                            actual_rest_ms = int((end_dt - start_dt).total_seconds() * 1000)
                            total_actual_rest_ms += actual_rest_ms
                            total_configured_rest_ms += rest.get("restDuration", rs.restDuration) * 1000
                        except ValueError:
                            pass
                if total_configured_rest_ms > 0:
                    rest_efficiency = total_actual_rest_ms / total_configured_rest_ms

            results.append(RunnerAnalyticsDTO(
                runner_id=rs.runner.id,
                runner_name=rs.runner.name,
                intervals=intervals_detail,
                overall_avg_pace=overall_avg_pace,
                rest_efficiency=rest_efficiency
            ))

        return results